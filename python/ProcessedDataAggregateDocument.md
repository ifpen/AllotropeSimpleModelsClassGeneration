# ProcessedDataAggregateDocument


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**processed_data_document** | [**List[ProcessedDataDocument]**](ProcessedDataDocument.md) | A processed data document is a document that encompasses the output of some data processing operation. | [optional] 

## Example

```python
from openapi_client.models.processed_data_aggregate_document import ProcessedDataAggregateDocument

# TODO update the JSON string below
json = "{}"
# create an instance of ProcessedDataAggregateDocument from a JSON string
processed_data_aggregate_document_instance = ProcessedDataAggregateDocument.from_json(json)
# print the JSON string representation of the object
print(ProcessedDataAggregateDocument.to_json())

# convert the object into a dict
processed_data_aggregate_document_dict = processed_data_aggregate_document_instance.to_dict()
# create an instance of ProcessedDataAggregateDocument from a dict
processed_data_aggregate_document_from_dict = ProcessedDataAggregateDocument.from_dict(processed_data_aggregate_document_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


