import React from 'react';
import ToolCall from './ToolCall';
import ToolResponse from './ToolResponse';

const Message = ({ message }) => {
  if (message.role === 'user') {
    const textPart = message.parts.find(p => p.type === 'text');
    return (
      <div className="message user">
        <div className="message-content">
          {textPart?.content}
        </div>
        <style jsx>{`
          .message.user {
            padding: 12px 18px;
            border-radius: 18px;
            margin-bottom: 12px;
            max-width: 80%;
            align-self: flex-end;
            margin-left: auto;
            background-color: #007aff;
            color: white;
          }
          .message-content {
            word-wrap: break-word;
            white-space: pre-wrap;
          }
        `}</style>
      </div>
    );
  }

  // Agent message - can have multiple parts (text, tool calls, tool responses)
  return (
    <div className="message agent">
      {message.parts.map((part, idx) => {
        if (part.type === 'text') {
          return (
            <div key={idx} className="agent-text">
              {part.content}
            </div>
          );
        } else if (part.type === 'tool_call') {
          return (
            <ToolCall
              key={idx}
              toolName={part.toolName}
              args={part.args}
              toolId={part.toolId}
            />
          );
        } else if (part.type === 'tool_response') {
          return (
            <ToolResponse
              key={idx}
              toolName={part.toolName}
              response={part.response}
              toolId={part.toolId}
            />
          );
        }
        return null;
      })}
      <style jsx>{`
        .message.agent {
          padding: 12px 18px;
          border-radius: 18px;
          margin-bottom: 12px;
          max-width: 85%;
          align-self: flex-start;
          background-color: #2a2a2a;
          color: #ededed;
        }
        .agent-text {
          margin-bottom: 10px;
          word-wrap: break-word;
          white-space: pre-wrap;
          line-height: 1.5;
        }
        .agent-text:last-child {
          margin-bottom: 0;
        }
      `}</style>
    </div>
  );
};

export default Message;
