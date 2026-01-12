# ChromatogramMeasure


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**component_data_type** | **str** |  | [optional] 
**scale** | **str** |  | [optional] 
**concept** | **str** |  | [optional] 
**unit** | **str** |  | [optional] 

## Example

```python
from openapi_client.models.chromatogram_measure import ChromatogramMeasure

# TODO update the JSON string below
json = "{}"
# create an instance of ChromatogramMeasure from a JSON string
chromatogram_measure_instance = ChromatogramMeasure.from_json(json)
# print the JSON string representation of the object
print(ChromatogramMeasure.to_json())

# convert the object into a dict
chromatogram_measure_dict = chromatogram_measure_instance.to_dict()
# create an instance of ChromatogramMeasure from a dict
chromatogram_measure_from_dict = ChromatogramMeasure.from_dict(chromatogram_measure_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


