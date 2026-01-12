# DeviceSystemDocument


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**asset_management_identifier** | **str** | An asset management identifier is an identifier that is registered within an asset / inventory management system that identifies an equipment. | 
**device_identifier** | **str** | A device identifier is an identifier that identifies some device. | [optional] 
**model_number** | **str** | A model number is an information content entity specifically borne by catalogs, design specifications, advertising materials, inventory systems and similar that is about manufactured objects of the same class. | [optional] 
**equipment_serial_number** | **str** | Equipment serial number is measurement metadata that identifies an equipment used in the measuring by its serial number. | [optional] 
**firmware_version** | **str** | A firmware version is a version number that identifies the firmware of a device. | [optional] 
**description** | **str** | A description is a proposition about an existing entity. | [optional] 
**brand_name** | **str** | A brand name is a marketed name given by a maker of a product to a product or class of products, especially a trademark. | [optional] 
**product_manufacturer** | **str** | An equipment manufacturer is a symbol that denotes the entity manufacturing the equipment. | [optional] 
**pump_model_number** | **str** | A pump model number is a model number that denotes some class of pumps. | [optional] 
**detector_model_number** | **str** | A detector model number is a model number that denotes some class of detectors. | [optional] 
**device_document** | [**List[DeviceDocument]**](DeviceDocument.md) | A device document is a document that encompasses the information associated with a device. | [optional] 

## Example

```python
from openapi_client.models.device_system_document import DeviceSystemDocument

# TODO update the JSON string below
json = "{}"
# create an instance of DeviceSystemDocument from a JSON string
device_system_document_instance = DeviceSystemDocument.from_json(json)
# print the JSON string representation of the object
print(DeviceSystemDocument.to_json())

# convert the object into a dict
device_system_document_dict = device_system_document_instance.to_dict()
# create an instance of DeviceSystemDocument from a dict
device_system_document_from_dict = DeviceSystemDocument.from_dict(device_system_document_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


