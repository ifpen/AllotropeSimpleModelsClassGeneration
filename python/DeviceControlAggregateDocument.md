# DeviceControlAggregateDocument


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**device_control_document** | [**List[DeviceControlDocument]**](DeviceControlDocument.md) | A device control document is a document that encompasses the information associated with control of a device. | 

## Example

```python
from openapi_client.models.device_control_aggregate_document import DeviceControlAggregateDocument

# TODO update the JSON string below
json = "{}"
# create an instance of DeviceControlAggregateDocument from a JSON string
device_control_aggregate_document_instance = DeviceControlAggregateDocument.from_json(json)
# print the JSON string representation of the object
print(DeviceControlAggregateDocument.to_json())

# convert the object into a dict
device_control_aggregate_document_dict = device_control_aggregate_document_instance.to_dict()
# create an instance of DeviceControlAggregateDocument from a dict
device_control_aggregate_document_from_dict = DeviceControlAggregateDocument.from_dict(device_control_aggregate_document_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


