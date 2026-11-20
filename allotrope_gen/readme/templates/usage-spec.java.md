```java
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.File;
import ${namespace}.${root};
import ${namespace}.client.ApiClient;

// The default mapper handles java.time values and the ASM "NaN" string.
ObjectMapper mapper = ApiClient.createDefaultObjectMapper();

${root} document = mapper.readValue(new File("input.json"), ${root}.class);
System.out.println(document.${java_documents}.size());

mapper.writeValue(new File("output.json"), document);
```
