# PeakPeakHeight

A peak facet that denotes the ordinate value of the peak extremum offset by the baseline ascribed to the peak.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**value** | **float** |  | 
**unit** | **str** |  | 

## Example

```python
from openapi_client.models.peak_peak_height import PeakPeakHeight

# TODO update the JSON string below
json = "{}"
# create an instance of PeakPeakHeight from a JSON string
peak_peak_height_instance = PeakPeakHeight.from_json(json)
# print the JSON string representation of the object
print(PeakPeakHeight.to_json())

# convert the object into a dict
peak_peak_height_dict = peak_peak_height_instance.to_dict()
# create an instance of PeakPeakHeight from a dict
peak_peak_height_from_dict = PeakPeakHeight.from_dict(peak_peak_height_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


