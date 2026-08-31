const compatible = new Set([
  '$schema', 'type', 'properties', 'required', 'additionalProperties', 'items',
  'enum', 'const', 'anyOf', 'oneOf', 'allOf', 'title', 'description', 'default',
  'minimum', 'maximum', 'exclusiveMinimum', 'exclusiveMaximum', 'multipleOf',
  'minLength', 'maxLength', 'pattern', 'format', 'minItems', 'maxItems',
  'uniqueItems', 'minProperties', 'maxProperties', 'contentEncoding', 'contentMediaType',
]);

export function modernSchema(schema) {
  if (typeof schema === 'boolean') return schema;
  if (!schema || typeof schema !== 'object' || Array.isArray(schema))
    throw new Error('Unsupported filesystem schema shape');
  const out = { ...schema };
  for (const key of Object.keys(out)) {
    if (!compatible.has(key)) throw new Error(`Unreviewed filesystem schema keyword: ${key}`);
    if (key === 'properties') out[key] = Object.fromEntries(Object.entries(out[key]).map(([k,v]) => [k,modernSchema(v)]));
    if (key === 'items' || (key === 'additionalProperties' && typeof out[key] === 'object')) out[key] = modernSchema(out[key]);
    if (['anyOf','oneOf','allOf'].includes(key)) out[key] = out[key].map(modernSchema);
    if (['exclusiveMinimum','exclusiveMaximum'].includes(key) && typeof out[key] !== 'number')
      throw new Error('Old boolean numeric bounds cannot be relabelled');
  }
  if ('$schema' in out) {
    if (out.$schema !== 'http://json-schema.org/draft-07/schema#') throw new Error('Unexpected filesystem schema dialect');
    out.$schema = 'https://json-schema.org/draft/2020-12/schema';
  }
  return out;
}
