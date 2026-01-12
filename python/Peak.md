# Peak


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**identifier** | **str** | An identifier is a name that identifies (that is, labels the identity of) either a unique object or a unique class of objects. | [optional] 
**written_name** | **str** |  | [optional] 
**peak_width_at_5__of_height** | [**PeakPeakWidthAt5OfHeight**](PeakPeakWidthAt5OfHeight.md) |  | [optional] 
**peak_width_at_baseline** | [**PeakPeakWidthAtBaseline**](PeakPeakWidthAtBaseline.md) |  | [optional] 
**peak_width_at_half_height** | [**PeakPeakWidthAtHalfHeight**](PeakPeakWidthAtHalfHeight.md) |  | [optional] 
**peak_height** | [**PeakPeakHeight**](PeakPeakHeight.md) |  | [optional] 
**asymmetry_factor_measured_at_5__height** | [**PeakAsymmetryFactorMeasuredAt5Height**](PeakAsymmetryFactorMeasuredAt5Height.md) |  | [optional] 
**statistical_skew** | [**PeakStatisticalSkew**](PeakStatisticalSkew.md) |  | [optional] 
**number_of_theoretical_plates_by_peak_width_at_half_height** | [**PeakNumberOfTheoreticalPlatesByPeakWidthAtHalfHeight**](PeakNumberOfTheoreticalPlatesByPeakWidthAtHalfHeight.md) |  | [optional] 
**number_of_theoretical_plates_by_tangent_method** | [**PeakNumberOfTheoreticalPlatesByTangentMethod**](PeakNumberOfTheoreticalPlatesByTangentMethod.md) |  | [optional] 
**retention_time** | [**PeakRetentionTime**](PeakRetentionTime.md) |  | 
**peak_area** | [**PeakPeakArea**](PeakPeakArea.md) |  | [optional] 
**peak_start** | [**PeakPeakStart**](PeakPeakStart.md) |  | [optional] 
**peak_end** | [**PeakPeakEnd**](PeakPeakEnd.md) |  | [optional] 
**capacity_factor__chromatography** | [**PeakCapacityFactorChromatography**](PeakCapacityFactorChromatography.md) |  | [optional] 
**relative_peak_height** | [**PeakRelativePeakHeight**](PeakRelativePeakHeight.md) |  | [optional] 
**relative_peak_area** | [**PeakRelativePeakArea**](PeakRelativePeakArea.md) |  | [optional] 
**peak_selectivity__chromatography** | [**PeakPeakSelectivityChromatography**](PeakPeakSelectivityChromatography.md) |  | [optional] 
**chromatographic_peak_resolution_using_baseline_peak_widths** | [**PeakChromatographicPeakResolutionUsingBaselinePeakWidths**](PeakChromatographicPeakResolutionUsingBaselinePeakWidths.md) |  | [optional] 
**chromatographic_peak_resolution_using_peak_width_at_half_height** | [**PeakChromatographicPeakResolutionUsingPeakWidthAtHalfHeight**](PeakChromatographicPeakResolutionUsingPeakWidthAtHalfHeight.md) |  | [optional] 
**chromatographic_peak_resolution_using_statistical_moments** | [**PeakChromatographicPeakResolutionUsingStatisticalMoments**](PeakChromatographicPeakResolutionUsingStatisticalMoments.md) |  | [optional] 

## Example

```python
from openapi_client.models.peak import Peak

# TODO update the JSON string below
json = "{}"
# create an instance of Peak from a JSON string
peak_instance = Peak.from_json(json)
# print the JSON string representation of the object
print(Peak.to_json())

# convert the object into a dict
peak_dict = peak_instance.to_dict()
# create an instance of Peak from a dict
peak_from_dict = Peak.from_dict(peak_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


