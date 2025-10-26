/**
 * Parse the complex A2A protocol response to extract all inter-agent communication
 */

/**
 * Parse a single message from the history
 */
export function parseMessage(message, index) {
  const parsed = {
    id: message.messageId || `msg-${index}`,
    role: message.role,
    contextId: message.contextId,
    taskId: message.taskId,
    parts: [],
  };

  if (!message.parts) return parsed;

  for (const part of message.parts) {
    if (part.kind === 'text') {
      parsed.parts.push({
        type: 'text',
        content: part.text,
      });
    } else if (part.kind === 'data') {
      // Check metadata to determine if this is a function call or response
      if (part.metadata?.adk_type === 'function_call') {
        parsed.parts.push({
          type: 'tool_call',
          toolName: part.data.name,
          toolId: part.data.id,
          args: part.data.args,
        });
      } else if (part.metadata?.adk_type === 'function_response') {
        parsed.parts.push({
          type: 'tool_response',
          toolName: part.data.name,
          toolId: part.data.id,
          response: part.data.response,
        });
      }
    }
  }

  return parsed;
}

/**
 * Check if a response looks like search results based on structure
 */
function isSearchResultResponse(response) {
  if (!response) return false;

  // Search results have a 'results' array and typically have metadata fields
  return (
    Array.isArray(response.results) &&
    (response.search_metadata || response.query || response.strategy)
  );
}

/**
 * Extract search results from tool responses
 * Works with any search tool that returns results array + metadata
 */
export function extractSearchResults(message) {
  if (message.role !== 'agent') return null;

  for (const part of message.parts) {
    if (part.type === 'tool_response' && isSearchResultResponse(part.response)) {
      console.log('Found search results from tool:', part.toolName);
      return {
        metadata: {
          query: part.response.search_metadata?.query || part.response.query,
          strategy: part.response.search_metadata?.strategy || part.response.strategy,
          resultCount: part.response.search_metadata?.result_count || part.response.final_count,
          scoreRange: part.response.search_metadata?.score_range,
        },
        results: part.response.results || [],
      };
    }
  }

  return null;
}

/**
 * Extract investigation plan from tool responses
 */
export function extractPlan(message) {
  if (message.role !== 'agent') return null;

  for (const part of message.parts) {
    if (part.type === 'tool_response' &&
        part.toolName === 'display_investigation_plan') {
      return part.response.plan;
    }
  }

  return null;
}

/**
 * Extract sub-agent communication from metadata
 */
export function extractSubAgentInfo(taskMetadata) {
  if (!taskMetadata) {
    console.log('No task metadata');
    return null;
  }

  const customMetadata = taskMetadata.adk_custom_metadata;
  if (!customMetadata) {
    console.log('No adk_custom_metadata');
    return null;
  }

  console.log('Custom metadata type:', typeof customMetadata);
  console.log('Custom metadata sample:', typeof customMetadata === 'string'
    ? customMetadata.substring(0, 500)
    : customMetadata);

  // The custom metadata contains stringified data, need to parse it
  // It includes a2a:request and a2a:response which show sub-agent communication
  try {
    // If it's a string, parse it carefully
    let metadata;
    if (typeof customMetadata === 'string') {
      // Python dict syntax is very similar to JavaScript object literals
      // We just need to replace a few Python-specific things
      let jsCode = customMetadata;

      // Replace all Python enum objects with their string values
      // Generic pattern: <EnumClass.value: 'string'> => 'string'
      jsCode = jsCode.replace(/<[A-Za-z_]+\.[A-Za-z_]+:\s*'([^']+)'>/g, "'$1'");
      jsCode = jsCode.replace(/<[A-Za-z_]+\.[A-Za-z_]+:\s*"([^"]+)">/g, '"$1"');

      // Replace Python literals with JavaScript equivalents
      jsCode = jsCode.replace(/\bNone\b/g, 'null');
      jsCode = jsCode.replace(/\bTrue\b/g, 'true');
      jsCode = jsCode.replace(/\bFalse\b/g, 'false');

      console.log('Attempting to parse as JavaScript object literal...');

      // Use Function constructor to evaluate the Python dict as JavaScript
      // This is safe because it's our own agent data
      try {
        const fn = new Function('return (' + jsCode + ')');
        metadata = fn();
        console.log('✓ Successfully parsed metadata');
      } catch (e) {
        console.error('Failed to parse metadata:', e.message);
        console.log('First 1000 chars of jsCode:', jsCode.substring(0, 1000));

        // Try to find the problematic part
        const match = e.message.match(/position (\d+)/);
        if (match) {
          const pos = parseInt(match[1]);
          console.log('Error near position', pos, ':', jsCode.substring(Math.max(0, pos - 50), pos + 50));
        }

        return null;
      }
    } else {
      metadata = customMetadata;
    }

    console.log('Parsed metadata keys:', Object.keys(metadata));

    const extracted = {
      taskId: metadata['a2a:task_id'],
      contextId: metadata['a2a:context_id'],
      request: metadata['a2a:request'],
      response: metadata['a2a:response'],
    };

    console.log('Extracted sub-agent info:', {
      hasTaskId: !!extracted.taskId,
      hasResponse: !!extracted.response,
      hasResponseResult: !!extracted.response?.result,
      hasHistory: !!extracted.response?.result?.history,
    });

    return extracted;
  } catch (e) {
    console.error('Failed to parse custom metadata:', e);
    return null;
  }
}

/**
 * Parse sub-agent history to extract thinking and results
 */
export function parseSubAgentCommunication(subAgentInfo) {
  if (!subAgentInfo || !subAgentInfo.response) return null;

  const response = subAgentInfo.response;
  const result = response.result;

  if (!result) return null;

  const history = result.history || [];
  const artifacts = result.artifacts || [];

  // Extract thinking from history
  const thinking = [];
  const toolCalls = [];
  const toolResponses = [];
  const searchResults = [];

  for (const message of history) {
    if (!message.parts) continue;

    for (const part of message.parts) {
      // Text parts are thinking
      if (part.kind === 'text') {
        thinking.push({
          text: part.text,
          role: message.role,
          messageId: message.messageId,
        });
      }
      // Data parts with function_call metadata are tool calls
      else if (part.kind === 'data') {
        if (part.metadata?.adk_type === 'function_call') {
          toolCalls.push({
            toolName: part.data.name,
            args: part.data.args,
            toolId: part.data.id,
          });
        } else if (part.metadata?.adk_type === 'function_response') {
          toolResponses.push({
            toolName: part.data.name,
            response: part.data.response,
            toolId: part.data.id,
          });

          // Extract search results if this response looks like search results
          // Works with any search tool that returns results array + metadata
          if (isSearchResultResponse(part.data.response)) {
            console.log('Found search tool response from:', part.data.name);
            console.log('Response keys:', Object.keys(part.data.response));
            console.log('Results count:', part.data.response.results?.length);

            const searchResult = {
              metadata: {
                query: part.data.response.search_metadata?.query || part.data.response.query,
                strategy: part.data.response.search_metadata?.strategy || part.data.response.strategy,
                resultCount: part.data.response.search_metadata?.result_count || part.data.response.results?.length || 0,
                scoreRange: part.data.response.search_metadata?.score_range,
              },
              results: part.data.response.results || [],
            };

            console.log('Extracted search result:', {
              toolName: part.data.name,
              query: searchResult.metadata.query,
              resultCount: searchResult.metadata.resultCount,
              actualResults: searchResult.results.length,
            });

            searchResults.push(searchResult);
          }
        }
      }
    }
  }

  return {
    taskId: result.id,
    status: result.status,
    metadata: result.metadata,
    thinking,
    toolCalls,
    toolResponses,
    artifacts,
    searchResults, // Include search results extracted from sub-agent
  };
}

/**
 * Process the entire history array
 */
export function processHistory(history) {
  if (!history) return { messages: [], plan: null, searchResults: [] };

  const messages = [];
  let plan = null;
  const searchResults = [];

  // Remove duplicate messages (same messageId)
  const seenMessageIds = new Set();
  const uniqueHistory = history.filter(msg => {
    if (seenMessageIds.has(msg.messageId)) {
      return false;
    }
    seenMessageIds.add(msg.messageId);
    return true;
  });

  for (let i = 0; i < uniqueHistory.length; i++) {
    const message = parseMessage(uniqueHistory[i], i);
    messages.push(message);

    // Extract plan if present
    const msgPlan = extractPlan(message);
    if (msgPlan) {
      plan = msgPlan;
    }

    // Extract search results if present
    const msgSearchResults = extractSearchResults(message);
    if (msgSearchResults) {
      searchResults.push(msgSearchResults);
    }
  }

  return { messages, plan, searchResults };
}

/**
 * Extract agent thinking from text parts
 */
export function extractAgentThinking(message) {
  if (message.role !== 'agent') return [];

  const thinking = [];
  for (const part of message.parts) {
    if (part.type === 'text') {
      thinking.push(part.content);
    }
  }

  return thinking;
}

/**
 * Extract tool usage summary
 */
export function extractToolUsage(messages) {
  const toolCalls = [];

  for (const message of messages) {
    if (message.role !== 'agent') continue;

    for (const part of message.parts) {
      if (part.type === 'tool_call') {
        toolCalls.push({
          messageId: message.id,
          toolName: part.toolName,
          toolId: part.toolId,
          args: part.args,
        });
      }
    }
  }

  return toolCalls;
}

/**
 * Get agent flow - shows the sequence of agent actions
 */
export function getAgentFlow(messages) {
  const flow = [];

  for (const message of messages) {
    if (message.role === 'user') {
      flow.push({
        type: 'user_query',
        content: message.parts.find(p => p.type === 'text')?.content,
      });
    } else if (message.role === 'agent') {
      for (const part of message.parts) {
        if (part.type === 'text') {
          flow.push({
            type: 'agent_thinking',
            content: part.content,
          });
        } else if (part.type === 'tool_call') {
          flow.push({
            type: 'tool_call',
            toolName: part.toolName,
            args: part.args,
          });
        } else if (part.type === 'tool_response') {
          flow.push({
            type: 'tool_response',
            toolName: part.toolName,
            response: part.response,
          });
        }
      }
    }
  }

  return flow;
}
