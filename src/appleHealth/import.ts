// Top level things: Record and Workout
//
// Record types:
//
// 1402587 "HKQuantityTypeIdentifierActiveEnergyBurned"
//  271037 "HKQuantityTypeIdentifierBasalEnergyBurned"
//  232910 "HKQuantityTypeIdentifierStepCount"
//  233329 "HKQuantityTypeIdentifierDistanceWalkingRunning"
//   14310 "HKQuantityTypeIdentifierFlightsClimbed"
//   12252 "HKQuantityTypeIdentifierDistanceCycling"
//
//  135795 "HKQuantityTypeIdentifierAppleExerciseTime"
//   59949 "HKQuantityTypeIdentifierAppleStandTime"
//   45880 "HKCategoryTypeIdentifierAppleStandHour"
//
//   17526 "HKCategoryTypeIdentifierSleepAnalysis"
//
//    1107 "HKQuantityTypeIdentifierDietaryEnergyConsumed"
//    1108 "HKQuantityTypeIdentifierDietaryProtein"
//    1107 "HKQuantityTypeIdentifierDietarySugar"
//    1107 "HKQuantityTypeIdentifierDietarySodium"
//    1107 "HKQuantityTypeIdentifierDietaryFatTotal"
//    1107 "HKQuantityTypeIdentifierDietaryFatSaturated"
//    1107 "HKQuantityTypeIdentifierDietaryCarbohydrates"
//    1049 "HKQuantityTypeIdentifierDietaryFiber"
//
//    1013 "HKQuantityTypeIdentifierBodyMass"
//    1003 "HKQuantityTypeIdentifierBodyMassIndex"
//     986 "HKQuantityTypeIdentifierBodyFatPercentage"
//     676 "HKQuantityTypeIdentifierLeanBodyMass"
//
//       3 "HKQuantityTypeIdentifierHeight"
//
//     191 "HKCategoryTypeIdentifierMindfulSession"
//
//      67 "HKCategoryTypeIdentifierHighHeartRateEvent"

//  563904 "HKQuantityTypeIdentifierHeartRate"
//   13238 "HKQuantityTypeIdentifierHeartRateVariabilitySDNN"
//    1957 "HKQuantityTypeIdentifierRestingHeartRate"
//    1830 "HKQuantityTypeIdentifierWalkingHeartRateAverage"
//   27135 "HKQuantityTypeIdentifierRespiratoryRate"
//   21926 "HKQuantityTypeIdentifierWalkingStepLength"
//   21921 "HKQuantityTypeIdentifierWalkingSpeed"
//   16847 "HKQuantityTypeIdentifierOxygenSaturation"
//   39015 "HKQuantityTypeIdentifierEnvironmentalAudioExposure"
//   15441 "HKQuantityTypeIdentifierHeadphoneAudioExposure"
//   10060 "HKQuantityTypeIdentifierWalkingDoubleSupportPercentage"
//    5772 "HKQuantityTypeIdentifierWalkingAsymmetryPercentage"
//    1513 "HKQuantityTypeIdentifierStairDescentSpeed"
//    1080 "HKQuantityTypeIdentifierStairAscentSpeed"
//      81 "HKQuantityTypeIdentifierAppleWalkingSteadiness"
//      81 "HKQuantityTypeIdentifierSixMinuteWalkTestDistance"
//       5 "HKCategoryTypeIdentifierAudioExposureEvent"
//       7 "HKQuantityTypeIdentifierDietaryWater"
//       1 "HKCategoryTypeIdentifierLowHeartRateEvent"
//       1 "HKDataTypeSleepDurationGoal"

// Example record:
//
// {
//   '$name': 'record',
//   metadataentry: [
//     { key: 'HKTimeZone', value: 'Europe/London' },
//     { key: 'HKWasUserEntered', value: '0' },
//     { key: 'Withings User Identifier', value: '<redacted>' },
//     { key: 'Modified Date', value: '2023-04-10 06:05:44 +0000' },
//     { key: 'HKExternalUUID', value: '<redacted>' },
//     { key: 'Health Mate App Version', value: '5.14.1' }
//   ],
//   '$attrs': {
//     type: 'HKQuantityTypeIdentifierBodyMass',
//     sourcename: 'Withings',
//     sourceversion: '5140101',
//     unit: 'lb',
//     creationdate: '2023-04-10 09:54:17 +0100',
//     startdate: '2023-04-10 07:05:24 +0100',
//     enddate: '2023-04-10 07:05:24 +0100',
//     value: '<redacted>'
//   }
// }
//
// {
//   '$name': 'record',
//   metadataentry: [
//     { key: 'diaryDateMetadataKey', value: '2023-04-18' },
//     {
//       key: 'HKExternalUUID',
//       value: '<redacted>'
//     }
//   ],
//   '$attrs': {
//     type: 'HKQuantityTypeIdentifierDietaryEnergyConsumed',
//     sourcename: 'Calorie Counter',
//     sourceversion: '1411',
//     unit: 'Cal',
//     creationdate: '2023-04-18 23:14:39 +0100',
//     startdate: '2023-04-18 00:00:00 +0100',
//     enddate: '2023-04-18 23:59:59 +0100',
//     value: '<redacted>'
//   }
// }

import {createReadStream} from "fs"
import flow from "xml-flow"

const xmlStream = flow(
  createReadStream(
    "/Users/davidmoody/Downloads/apple_health_export/export.xml",
  ),
)

// xmlStream.on("tag:record", (x: any) => {
//   if (x.$attrs?.type === "HKQuantityTypeIdentifierBodyMass") {
//     const date = x.$attrs.startdate?.split(" ")[0]
//     const value = parseFloat(x.$attrs.value)
//     const unit = x.$attrs.unit

//     // TODO remove duplicates for some days where there are multiple measurements
//     console.log(`${date} ${value.toFixed(1)}${unit}`)
//   }
// })

xmlStream.on("tag:record", (x: any) => {
  if (x.$attrs?.type === "HKQuantityTypeIdentifierDietaryEnergyConsumed") {
    const date = x.$attrs.startdate?.split(" ")[0]
    const value = parseFloat(x.$attrs.value)
    // const unit = x.$attrs.unit

    console.log(`${date} ${value}`)
  }
})
