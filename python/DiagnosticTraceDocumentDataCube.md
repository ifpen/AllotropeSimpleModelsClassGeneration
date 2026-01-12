# DiagnosticTraceDocumentDataCube

Represents a collection of observations, possibly organized into various slices, conforming to some common dimensional structure.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**label** | **str** |  | [optional] 
**datacube_structure** | [**DiagnosticTraceDocumentDataCubeDatacubeStructure**](DiagnosticTraceDocumentDataCubeDatacubeStructure.md) |  | [optional] 
**datacube_data** | [**DiagnosticTraceDocumentDataCubeDatacubeData**](DiagnosticTraceDocumentDataCubeDatacubeData.md) |  | [optional] 

## Example

```python
from openapi_client.models.diagnostic_trace_document_data_cube import DiagnosticTraceDocumentDataCube

# TODO update the JSON string below
json = "{}"
# create an instance of DiagnosticTraceDocumentDataCube from a JSON string
diagnostic_trace_document_data_cube_instance = DiagnosticTraceDocumentDataCube.from_json(json)
# print the JSON string representation of the object
print(DiagnosticTraceDocumentDataCube.to_json())

# convert the object into a dict
diagnostic_trace_document_data_cube_dict = diagnostic_trace_document_data_cube_instance.to_dict()
# create an instance of DiagnosticTraceDocumentDataCube from a dict
diagnostic_trace_document_data_cube_from_dict = DiagnosticTraceDocumentDataCube.from_dict(diagnostic_trace_document_data_cube_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


