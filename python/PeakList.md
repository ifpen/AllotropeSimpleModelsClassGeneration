# PeakList


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**peak** | [**List[Peak]**](Peak.md) | A peak is a data region containing a single local extremum in the dependent variable of the distribution function. | 

## Example

```python
from openapi_client.models.peak_list import PeakList

# TODO update the JSON string below
json = "{}"
# create an instance of PeakList from a JSON string
peak_list_instance = PeakList.from_json(json)
# print the JSON string representation of the object
print(PeakList.to_json())

# convert the object into a dict
peak_list_dict = peak_list_instance.to_dict()
# create an instance of PeakList from a dict
peak_list_from_dict = PeakList.from_dict(peak_list_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


