# ChromatogramDataCube


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**label** | **str** |  | [optional] 
**datacube_structure** | [**ChromatogramDatacubeStructure**](ChromatogramDatacubeStructure.md) |  | [optional] 
**datacube_data** | [**DatacubeData**](DatacubeData.md) |  | [optional] 

## Example

```python
from openapi_client.models.chromatogram_data_cube import ChromatogramDataCube

# TODO update the JSON string below
json = "{}"
# create an instance of ChromatogramDataCube from a JSON string
chromatogram_data_cube_instance = ChromatogramDataCube.from_json(json)
# print the JSON string representation of the object
print(ChromatogramDataCube.to_json())

# convert the object into a dict
chromatogram_data_cube_dict = chromatogram_data_cube_instance.to_dict()
# create an instance of ChromatogramDataCube from a dict
chromatogram_data_cube_from_dict = ChromatogramDataCube.from_dict(chromatogram_data_cube_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


