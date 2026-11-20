    public class ${model}JsonConverter : JsonConverter<${model}>
    {
        // Replaced by allotrope_gen (allotrope_gen/patch/csharp.py, patch_primitive_unions):
        // the generated oneOf converter only handled JSON objects, so the
        // ${json_kind} variant was neither read nor written.

        /// <summary>
        /// Deserializes a JSON ${json_kind} or a typed value object to <see cref="${model}" />
        /// </summary>
        /// <param name="utf8JsonReader"></param>
        /// <param name="typeToConvert"></param>
        /// <param name="jsonSerializerOptions"></param>
        /// <returns></returns>
        /// <exception cref="JsonException"></exception>
        public override ${model} Read(ref Utf8JsonReader utf8JsonReader, Type typeToConvert, JsonSerializerOptions jsonSerializerOptions)
        {
            switch (utf8JsonReader.TokenType)
            {
${primitive_cases}
                    return new ${model}(JsonSerializer.Deserialize<${primitive_type}>(ref utf8JsonReader, jsonSerializerOptions));
                case JsonTokenType.StartObject:
                    return new ${model}(JsonSerializer.Deserialize<${object_type}>(ref utf8JsonReader, jsonSerializerOptions));
                default:
                    throw new JsonException("Expected a JSON ${json_kind} or object for ${model}, found " + utf8JsonReader.TokenType + ".");
            }
        }

        /// <summary>
        /// Serializes a <see cref="${model}" /> as its ${json_kind} or typed value object
        /// </summary>
        /// <param name="writer"></param>
        /// <param name="${variable}"></param>
        /// <param name="jsonSerializerOptions"></param>
        /// <exception cref="JsonException"></exception>
        public override void Write(Utf8JsonWriter writer, ${model} ${variable}, JsonSerializerOptions jsonSerializerOptions)
        {
            if (${variable}.${primitive_property} != null)
                JsonSerializer.Serialize(writer, ${primitive_value}, jsonSerializerOptions);
            else if (${variable}.${object_property} != null)
                JsonSerializer.Serialize(writer, ${variable}.${object_property}, jsonSerializerOptions);
            else
                throw new JsonException("${model} has neither a ${json_kind} nor an object value.");
        }
    }
