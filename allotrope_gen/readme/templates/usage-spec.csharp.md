```csharp
using System;
using System.IO;
using System.Text.Json;
using Microsoft.Extensions.DependencyInjection;
using ${namespace}.Client;
using ${namespace}.Model;

// HostConfiguration registers the JSON converters of this package and of the
// commons package; the options must come from it.
var services = new ServiceCollection();
new HostConfiguration(services);
var options = services.BuildServiceProvider()
    .GetRequiredService<JsonSerializerOptionsProvider>().Options;

var document = JsonSerializer.Deserialize<${root}>(File.ReadAllText("input.json"), options);
Console.WriteLine(document.${csharp_documents}.Count);

File.WriteAllText("output.json", JsonSerializer.Serialize(document, options));
```
