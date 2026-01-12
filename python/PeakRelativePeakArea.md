# PeakRelativePeakArea

A peak facet that denotes the area of the peak relative to some other peak or summation of peaks.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**value** | **float** |  | 
**unit** | **str** |  | 

## Example

```python
from openapi_client.models.peak_relative_peak_area import PeakRelativePeakArea

# TODO update the JSON string below
json = "{}"
# create an instance of PeakRelativePeakArea from a JSON string
peak_relative_peak_area_instance = PeakRelativePeakArea.from_json(json)
# print the JSON string representation of the object
print(PeakRelativePeakArea.to_json())

# convert the object into a dict
peak_relative_peak_area_dict = peak_relative_peak_area_instance.to_dict()
# create an instance of PeakRelativePeakArea from a dict
peak_relative_peak_area_from_dict = PeakRelativePeakArea.from_dict(peak_relative_peak_area_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


