# DiagnosticTraceDocumentDataCubeDatacubeStructure


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**dimensions** | [**List[DiagnosticTraceDocumentDataCubeDatacubeStructureDimensionsInner]**](DiagnosticTraceDocumentDataCubeDatacubeStructureDimensionsInner.md) |  | [optional] 
**measures** | [**List[DiagnosticTraceDocumentDataCubeDatacubeStructureDimensionsInner]**](DiagnosticTraceDocumentDataCubeDatacubeStructureDimensionsInner.md) |  | [optional] 

## Example

```python
from openapi_client.models.diagnostic_trace_document_data_cube_datacube_structure import DiagnosticTraceDocumentDataCubeDatacubeStructure

# TODO update the JSON string below
json = "{}"
# create an instance of DiagnosticTraceDocumentDataCubeDatacubeStructure from a JSON string
diagnostic_trace_document_data_cube_datacube_structure_instance = DiagnosticTraceDocumentDataCubeDatacubeStructure.from_json(json)
# print the JSON string representation of the object
print(DiagnosticTraceDocumentDataCubeDatacubeStructure.to_json())

# convert the object into a dict
diagnostic_trace_document_data_cube_datacube_structure_dict = diagnostic_trace_document_data_cube_datacube_structure_instance.to_dict()
# create an instance of DiagnosticTraceDocumentDataCubeDatacubeStructure from a dict
diagnostic_trace_document_data_cube_datacube_structure_from_dict = DiagnosticTraceDocumentDataCubeDatacubeStructure.from_dict(diagnostic_trace_document_data_cube_datacube_structure_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


