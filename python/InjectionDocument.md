# InjectionDocument


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**injection_identifier** | **str** |  | 
**injection_volume_setting** | [**InjectionDocumentInjectionVolumeSetting**](InjectionDocumentInjectionVolumeSetting.md) |  | 
**injection_time** | **datetime** |  | 

## Example

```python
from openapi_client.models.injection_document import InjectionDocument

# TODO update the JSON string below
json = "{}"
# create an instance of InjectionDocument from a JSON string
injection_document_instance = InjectionDocument.from_json(json)
# print the JSON string representation of the object
print(InjectionDocument.to_json())

# convert the object into a dict
injection_document_dict = injection_document_instance.to_dict()
# create an instance of InjectionDocument from a dict
injection_document_from_dict = InjectionDocument.from_dict(injection_document_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


