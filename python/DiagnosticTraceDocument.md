# DiagnosticTraceDocument


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**description** | **str** | A description is a proposition about an existing entity. | 
**data_cube** | [**DiagnosticTraceDocumentDataCube**](DiagnosticTraceDocumentDataCube.md) |  | [optional] 

## Example

```python
from openapi_client.models.diagnostic_trace_document import DiagnosticTraceDocument

# TODO update the JSON string below
json = "{}"
# create an instance of DiagnosticTraceDocument from a JSON string
diagnostic_trace_document_instance = DiagnosticTraceDocument.from_json(json)
# print the JSON string representation of the object
print(DiagnosticTraceDocument.to_json())

# convert the object into a dict
diagnostic_trace_document_dict = diagnostic_trace_document_instance.to_dict()
# create an instance of DiagnosticTraceDocument from a dict
diagnostic_trace_document_from_dict = DiagnosticTraceDocument.from_dict(diagnostic_trace_document_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


