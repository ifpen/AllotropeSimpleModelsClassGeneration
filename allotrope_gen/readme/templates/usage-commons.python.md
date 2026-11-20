```python
from ${namespace} import QuantityValue

retention_time = QuantityValue(value=12.5, unit="s")
print(retention_time.to_json())  # {"value": 12.5, "unit": "s"}
```
