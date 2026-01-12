# SampleDocument


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**description** | **str** | A description is a proposition about an existing entity. | [optional] 
**sample_identifier** | **str** | Sample id is a measurement metadata that identifies a sample being measured. | 
**batch_identifier** | **str** | A batch identifier is an identifier that identifies a batch. | [optional] 
**sample_role_type** | **str** | A sample role type is a classification datum that classifies samples by the type of sample role in the experiment. | [optional] 
**written_name** | **str** | A textual entity that denotes a particular in reality. | [optional] 
**sampling_type** | **str** | A sampling type is a classification datum that classifies the type of sampling approach used to take a sample. | [optional] 

## Example

```python
from openapi_client.models.sample_document import SampleDocument

# TODO update the JSON string below
json = "{}"
# create an instance of SampleDocument from a JSON string
sample_document_instance = SampleDocument.from_json(json)
# print the JSON string representation of the object
print(SampleDocument.to_json())

# convert the object into a dict
sample_document_dict = sample_document_instance.to_dict()
# create an instance of SampleDocument from a dict
sample_document_from_dict = SampleDocument.from_dict(sample_document_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


