// Compatibility for Claude Desktop's JSON Schema 2020-12 output validator.
// The pinned official server emits draft-07 for these structurally compatible
// schemas. Preserve validation and tool behavior; do not remove outputSchema.
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { modernSchema } from './schema-compat.mjs';

const originalSend = StdioServerTransport.prototype.send;
StdioServerTransport.prototype.send = function(message) {
  if (Array.isArray(message.result?.tools)) {
    message = {...message, result: {...message.result, tools: message.result.tools.map(tool => ({
      ...tool,
      inputSchema: modernSchema(tool.inputSchema),
      ...(tool.outputSchema ? {outputSchema: modernSchema(tool.outputSchema)} : {}),
    }))}};
  }
  return originalSend.call(this, message);
};
await import('@modelcontextprotocol/server-filesystem/dist/index.js');

