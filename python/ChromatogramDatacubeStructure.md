# ChromatogramDatacubeStructure


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**dimensions** | [**List[ChromatogramDimension]**](ChromatogramDimension.md) |  | [optional] 
**measures** | [**List[ChromatogramMeasure]**](ChromatogramMeasure.md) |  | [optional] 

## Example

```python
from openapi_client.models.chromatogram_datacube_structure import ChromatogramDatacubeStructure

# TODO update the JSON string below
json = "{}"
# create an instance of ChromatogramDatacubeStructure from a JSON string
chromatogram_datacube_structure_instance = ChromatogramDatacubeStructure.from_json(json)
# print the JSON string representation of the object
print(ChromatogramDatacubeStructure.to_json())

# convert the object into a dict
chromatogram_datacube_structure_dict = chromatogram_datacube_structure_instance.to_dict()
# create an instance of ChromatogramDatacubeStructure from a dict
chromatogram_datacube_structure_from_dict = ChromatogramDatacubeStructure.from_dict(chromatogram_datacube_structure_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


