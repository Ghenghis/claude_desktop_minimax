import { test } from 'node:test';
import assert from 'node:assert/strict';
import { modernSchema } from '../mcp-runtime/schema-compat.mjs';

test('preserves nested output constraints and does not mutate the source', () => {
  const input = {$schema:'http://json-schema.org/draft-07/schema#', type:'object',
    properties:{text:{type:'string',minLength:3}}, required:['text'], additionalProperties:false};
  const before = JSON.stringify(input);
  const output = modernSchema(input);
  assert.equal(output.$schema, 'https://json-schema.org/draft/2020-12/schema');
  assert.deepEqual(output.properties, input.properties);
  assert.deepEqual(output.required, ['text']);
  assert.equal(output.additionalProperties, false);
  assert.equal(JSON.stringify(input), before);
});
test('fails closed on dialect features that require semantic conversion', () => {
  for (const schema of [
    {dependencies:{x:['y']}}, {items:[{type:'string'}]},
    {exclusiveMinimum:true}, {$ref:'#/definitions/x'},
    {$schema:'https://json-schema.org/draft/2019-09/schema'},
    {properties:{nested:{additionalItems:false}}},
  ]) assert.throws(() => modernSchema(schema));
});
test('retains alternatives, boolean schemas, and array item constraints', () => {
  assert.deepEqual(modernSchema({anyOf:[false,{type:'array',items:{type:'integer',minimum:1}}]}),
    {anyOf:[false,{type:'array',items:{type:'integer',minimum:1}}]});
});
