"""
WebSocket Server for Radiology Agent
Connects frontend to deployed Vertex AI agent
"""
import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, Set

import vertexai
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

# Load environment variables
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "radiology-agent")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
AGENT_ID = os.getenv("AGENT_ID", "8165505511492419584")

# Initialize Vertex AI client
client = vertexai.Client(project=PROJECT_ID, location=LOCATION)

# Get deployed agent
agent_resource_name = f"projects/{PROJECT_ID}/locations/{LOCATION}/reasoningEngines/{AGENT_ID}"
try:
    remote_app = client.agent_engines.get(name=agent_resource_name)
    logger.info(f"✅ Connected to agent: {agent_resource_name}")
except Exception as e:
    logger.error(f"❌ Failed to connect to agent: {e}")
    remote_app = None

# FastAPI app
app = FastAPI(title="Radiology Agent WebSocket Server")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080",
        "*"  # Allow all for development - restrict in production
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Active connections
active_connections: Set[WebSocket] = set()


class ConnectionManager:
    """Manages WebSocket connections and agent sessions"""

    def __init__(self):
        self.active_sessions: Dict[str, str] = {}  # websocket_id -> session_id

    async def connect(self, websocket: WebSocket) -> str:
        """Accept WebSocket connection and create agent session"""
        await websocket.accept()
        active_connections.add(websocket)

        # Create unique user ID for this connection
        user_id = f"user_{id(websocket)}"

        # Create agent session
        try:
            session = await remote_app.async_create_session(user_id=user_id)
            session_id = session["id"]
            self.active_sessions[user_id] = session_id
            logger.info(f"✅ New connection: {user_id}, session: {session_id}")
            return user_id
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            raise

    def disconnect(self, user_id: str, websocket: WebSocket):
        """Remove WebSocket connection"""
        active_connections.discard(websocket)
        if user_id in self.active_sessions:
            del self.active_sessions[user_id]
        logger.info(f"❌ Disconnected: {user_id}")

    async def send_json(self, websocket: WebSocket, data: dict):
        """Send JSON message to WebSocket"""
        try:
            await websocket.send_json(data)
        except Exception as e:
            logger.error(f"Error sending message: {e}")

    async def handle_query(self, websocket: WebSocket, user_id: str, message: str):
        """Handle user query and stream agent response"""
        session_id = self.active_sessions.get(user_id)
        if not session_id:
            await self.send_json(websocket, {
                "type": "error",
                "data": {"message": "No active session"}
            })
            return

        # Send acknowledgment
        await self.send_json(websocket, {
            "type": "query_received",
            "data": {"query": message}
        })

        try:
            # Stream query to agent
            async for event in remote_app.async_stream_query(
                user_id=user_id,
                session_id=session_id,
                message=message,
            ):
                # Parse and forward events to frontend
                await self.process_event(websocket, event)

            # Send completion
            await self.send_json(websocket, {
                "type": "completed",
                "data": {"message": "Investigation complete"}
            })

        except Exception as e:
            logger.error(f"Error during query: {e}")
            await self.send_json(websocket, {
                "type": "error",
                "data": {"message": str(e)}
            })

    async def process_event(self, websocket: WebSocket, event: dict):
        """Process agent event and send to frontend"""

        # Extract content
        if not isinstance(event, dict) or 'content' not in event:
            return

        content = event['content']
        if 'parts' not in content:
            return

        for part in content['parts']:
            # Investigation plan
            if 'function_call' in part:
                fc = part['function_call']
                if fc['name'] == 'display_investigation_plan':
                    plan_json = fc['args'].get('plan_json', '[]')
                    try:
                        plan = json.loads(plan_json)
                        await self.send_json(websocket, {
                            "type": "investigation_plan",
                            "data": {"plan": plan}
                        })
                    except:
                        pass

                # Tool call
                else:
                    await self.send_json(websocket, {
                        "type": "tool_call",
                        "data": {
                            "tool": fc['name'],
                            "args": fc.get('args', {})
                        }
                    })

            # Function response (tool results)
            if 'function_response' in part:
                fr = part['function_response']

                # Step update
                if fr['name'] == 'update_step_status':
                    response = fr.get('response', {})
                    await self.send_json(websocket, {
                        "type": "step_update",
                        "data": {
                            "step_number": response.get('step'),
                            "status": response.get('new_status'),
                        }
                    })

                # Search results
                elif 'search' in fr['name'].lower():
                    if 'actions' in event and 'state_delta' in event['actions']:
                        state = event['actions']['state_delta']
                        if 'search_results' in state:
                            search_results_obj = state['search_results']
                            reports = []
                            # Handle both dict and list for reports
                            if isinstance(search_results_obj, dict):
                                reports = search_results_obj.get('results', [])
                            elif isinstance(search_results_obj, list):
                                reports = search_results_obj

                            # Get metadata from top-level state delta
                            search_metadata = state.get('search_metadata', {})

                            await self.send_json(websocket, {
                                "type": "search_results",
                                "data": {
                                    "reports": reports[:10],
                                    "count": len(reports),
                                    "search_metadata": search_metadata
                                }
                            })

                # Vision results
                elif 'vision' in fr['name'].lower():
                    if 'actions' in event and 'state_delta' in event['actions']:
                        state = event['actions']['state_delta']
                        if 'vision_similar_images' in state:
                            await self.send_json(websocket, {
                                "type": "vision_results",
                                "data": {
                                    "similar_cases": state['vision_similar_images'],
                                    "metadata": state.get('vision_metadata', {})
                                }
                            })

            # Text response
            if 'text' in part:
                await self.send_json(websocket, {
                    "type": "agent_message",
                    "data": {"message": part['text']}
                })


manager = ConnectionManager()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for agent communication"""

    if not remote_app:
        await websocket.close(code=1011, reason="Agent not available")
        return

    user_id = None
    try:
        # Connect and create session
        user_id = await manager.connect(websocket)

        # Send connection confirmation
        await manager.send_json(websocket, {
            "type": "connected",
            "data": {"message": "Connected to Radiology Agent", "user_id": user_id}
        })

        # Listen for messages
        while True:
            data = await websocket.receive_json()

            if "query" in data:
                query = data["query"]
                logger.info(f"Query from {user_id}: {query}")
                await manager.handle_query(websocket, user_id, query)

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {user_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        if user_id:
            manager.disconnect(user_id, websocket)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "agent_connected": remote_app is not None,
        "agent_id": AGENT_ID,
        "active_connections": len(active_connections)
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Radiology Agent WebSocket Server",
        "version": "1.0.0",
        "websocket_url": "/ws",
        "agent_status": "connected" if remote_app else "disconnected"
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    logger.info(f"🚀 Starting server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
