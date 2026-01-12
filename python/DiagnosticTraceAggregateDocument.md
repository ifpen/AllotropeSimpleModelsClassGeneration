# DiagnosticTraceAggregateDocument


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**diagnostic_trace_document** | [**DiagnosticTraceDocument**](DiagnosticTraceDocument.md) | A processed data document is a document that encompasses the output of some data processing operation. | [optional] 

## Example

```python
from openapi_client.models.diagnostic_trace_aggregate_document import DiagnosticTraceAggregateDocument

# TODO update the JSON string below
json = "{}"
# create an instance of DiagnosticTraceAggregateDocument from a JSON string
diagnostic_trace_aggregate_document_instance = DiagnosticTraceAggregateDocument.from_json(json)
# print the JSON string representation of the object
print(DiagnosticTraceAggregateDocument.to_json())

# convert the object into a dict
diagnostic_trace_aggregate_document_dict = diagnostic_trace_aggregate_document_instance.to_dict()
# create an instance of DiagnosticTraceAggregateDocument from a dict
diagnostic_trace_aggregate_document_from_dict = DiagnosticTraceAggregateDocument.from_dict(diagnostic_trace_aggregate_document_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


