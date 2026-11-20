Technique packages register the commons converters in their
`HostConfiguration`. To serialize commons models with your own options, add
the converters yourself:

```csharp
using System.Text.Json;
using ${namespace}.Client;
using ${namespace}.Model;

var options = new JsonSerializerOptions();
CommonsJsonConverters.AddTo(options);

var retentionTime = new QuantityValue(12.5, unit: new Option<string>("s"));
string json = JsonSerializer.Serialize(retentionTime, options);  // {"value":12.5,"unit":"s"}
```
