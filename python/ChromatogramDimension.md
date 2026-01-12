# ChromatogramDimension


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**component_data_type** | **str** |  | [optional] 
**scale** | **str** |  | [optional] 
**concept** | **str** |  | [optional] 
**unit** | **str** |  | [optional] 

## Example

```python
from openapi_client.models.chromatogram_dimension import ChromatogramDimension

# TODO update the JSON string below
json = "{}"
# create an instance of ChromatogramDimension from a JSON string
chromatogram_dimension_instance = ChromatogramDimension.from_json(json)
# print the JSON string representation of the object
print(ChromatogramDimension.to_json())

# convert the object into a dict
chromatogram_dimension_dict = chromatogram_dimension_instance.to_dict()
# create an instance of ChromatogramDimension from a dict
chromatogram_dimension_from_dict = ChromatogramDimension.from_dict(chromatogram_dimension_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


