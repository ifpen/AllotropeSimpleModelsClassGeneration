# GasChromatographySimpleModel


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**gas_chromatography_aggregate_document** | [**GasChromatographyAggregateDocument**](GasChromatographyAggregateDocument.md) |  | [optional] 
**asm_manifest** | **str** |  | [optional] [default to 'http://purl.allotrope.org/manifests/gas-chromatography/REC/2025/06/gas-chromatography.tabular.manifest']

## Example

```python
from openapi_client.models.gas_chromatography_simple_model import GasChromatographySimpleModel

# TODO update the JSON string below
json = "{}"
# create an instance of GasChromatographySimpleModel from a JSON string
gas_chromatography_simple_model_instance = GasChromatographySimpleModel.from_json(json)
# print the JSON string representation of the object
print(GasChromatographySimpleModel.to_json())

# convert the object into a dict
gas_chromatography_simple_model_dict = gas_chromatography_simple_model_instance.to_dict()
# create an instance of GasChromatographySimpleModel from a dict
gas_chromatography_simple_model_from_dict = GasChromatographySimpleModel.from_dict(gas_chromatography_simple_model_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


