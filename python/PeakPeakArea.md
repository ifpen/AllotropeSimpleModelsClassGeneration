# PeakPeakArea

A peak facet that quantitates the area enclosed by a peak and the selected baseline.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**value** | **float** |  | 
**unit** | **str** |  | 

## Example

```python
from openapi_client.models.peak_peak_area import PeakPeakArea

# TODO update the JSON string below
json = "{}"
# create an instance of PeakPeakArea from a JSON string
peak_peak_area_instance = PeakPeakArea.from_json(json)
# print the JSON string representation of the object
print(PeakPeakArea.to_json())

# convert the object into a dict
peak_peak_area_dict = peak_peak_area_instance.to_dict()
# create an instance of PeakPeakArea from a dict
peak_peak_area_from_dict = PeakPeakArea.from_dict(peak_peak_area_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


