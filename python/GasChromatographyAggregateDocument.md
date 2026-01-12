# GasChromatographyAggregateDocument


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**device_system_document** | [**DeviceSystemDocument**](DeviceSystemDocument.md) |  | 
**gas_chromatography_document** | [**List[GasChromatographyDocument]**](GasChromatographyDocument.md) |  | 

## Example

```python
from openapi_client.models.gas_chromatography_aggregate_document import GasChromatographyAggregateDocument

# TODO update the JSON string below
json = "{}"
# create an instance of GasChromatographyAggregateDocument from a JSON string
gas_chromatography_aggregate_document_instance = GasChromatographyAggregateDocument.from_json(json)
# print the JSON string representation of the object
print(GasChromatographyAggregateDocument.to_json())

# convert the object into a dict
gas_chromatography_aggregate_document_dict = gas_chromatography_aggregate_document_instance.to_dict()
# create an instance of GasChromatographyAggregateDocument from a dict
gas_chromatography_aggregate_document_from_dict = GasChromatographyAggregateDocument.from_dict(gas_chromatography_aggregate_document_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


