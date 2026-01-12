# ProcessedDataDocument


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**peak_list** | [**PeakList**](PeakList.md) | Collection of peaks or peak groups for a specific purpose. | 

## Example

```python
from openapi_client.models.processed_data_document import ProcessedDataDocument

# TODO update the JSON string below
json = "{}"
# create an instance of ProcessedDataDocument from a JSON string
processed_data_document_instance = ProcessedDataDocument.from_json(json)
# print the JSON string representation of the object
print(ProcessedDataDocument.to_json())

# convert the object into a dict
processed_data_document_dict = processed_data_document_instance.to_dict()
# create an instance of ProcessedDataDocument from a dict
processed_data_document_from_dict = ProcessedDataDocument.from_dict(processed_data_document_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


