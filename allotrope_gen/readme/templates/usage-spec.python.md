```python
from ${namespace} import ${root}

with open("input.json", encoding="utf-8") as stream:
    document = ${root}.from_json(stream.read())
print(len(document.${python_documents}))

with open("output.json", "w", encoding="utf-8") as stream:
    stream.write(document.to_json())
```
