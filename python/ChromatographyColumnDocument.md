# ChromatographyColumnDocument


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**chromatography_column_part_number** | **str** | A column part number is a part number that denotes some class of chromatography columns. | [optional] 
**chromatography_column_serial_number** | **str** | A column serial number is an equipment serial number that identifies some chromatography column. | 
**chromatography_column_length** | [**ChromatographyColumnDocumentChromatographyColumnLength**](ChromatographyColumnDocumentChromatographyColumnLength.md) |  | [optional] 
**column_inner_diameter** | [**ChromatographyColumnDocumentColumnInnerDiameter**](ChromatographyColumnDocumentColumnInnerDiameter.md) |  | [optional] 
**chromatography_column_chemistry_type** | **str** | A chromatography column chemistry type is a classification datum that classifies a chromatography column by the stationary phase and/or chromatographic packing used. | [optional] 
**chromatography_column_particle_size** | [**ChromatographyColumnDocumentChromatographyColumnParticleSize**](ChromatographyColumnDocumentChromatographyColumnParticleSize.md) |  | [optional] 
**product_manufacturer** | **str** | A product manufacturer is a symbol that denotes the organizational entity manufacturing some entity with a product role (economic). | [optional] 
**chromatography_column_fill_type** | **str** | A chromatography column fill type is a classification datum that classifies a chromatography column by the form of the stationary phase in the column. | [optional] 

## Example

```python
from openapi_client.models.chromatography_column_document import ChromatographyColumnDocument

# TODO update the JSON string below
json = "{}"
# create an instance of ChromatographyColumnDocument from a JSON string
chromatography_column_document_instance = ChromatographyColumnDocument.from_json(json)
# print the JSON string representation of the object
print(ChromatographyColumnDocument.to_json())

# convert the object into a dict
chromatography_column_document_dict = chromatography_column_document_instance.to_dict()
# create an instance of ChromatographyColumnDocument from a dict
chromatography_column_document_from_dict = ChromatographyColumnDocument.from_dict(chromatography_column_document_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


