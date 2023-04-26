// Top level things: Record and Workout
//
// Record types:
//
//   17526 "HKCategoryTypeIdentifierSleepAnalysis"

// Example record:
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

import {createReadStream, writeFileSync} from "fs"
import flow from "xml-flow"

const xmlStream = flow(
  createReadStream(
    process.env.HOME + "/Downloads/apple_health_export/export.xml",
  ),
  {
    trim: false,
    normalize: false,
    simplifyNodes: false,
  },
)

const recordParsers: Record<string, {shortType: string; expectedUnit: string}> =
  {
    HKQuantityTypeIdentifierBodyMass: {
      shortType: "bodyMassLb",
      expectedUnit: "lb",
    },
    HKQuantityTypeIdentifierBodyFatPercentage: {
      shortType: "bodyFat",
      expectedUnit: "%",
    },
    HKQuantityTypeIdentifierLeanBodyMass: {
      shortType: "leanBodyMassKg",
      expectedUnit: "kg",
    },
    HKQuantityTypeIdentifierBodyMassIndex: {
      shortType: "bodyMassIndex",
      expectedUnit: "count",
    },

    HKQuantityTypeIdentifierDietaryEnergyConsumed: {
      shortType: "eatenCalories",
      expectedUnit: "Cal",
    },
    HKQuantityTypeIdentifierDietaryProtein: {
      shortType: "eatenProtein",
      expectedUnit: "g",
    },
    HKQuantityTypeIdentifierDietarySugar: {
      shortType: "eatenSugar",
      expectedUnit: "g",
    },
    HKQuantityTypeIdentifierDietarySodium: {
      shortType: "eatenSodium",
      expectedUnit: "mg",
    },
    HKQuantityTypeIdentifierDietaryFatTotal: {
      shortType: "eatenFat",
      expectedUnit: "g",
    },
    HKQuantityTypeIdentifierDietaryFatSaturated: {
      shortType: "eatenFatSaturated",
      expectedUnit: "g",
    },
    HKQuantityTypeIdentifierDietaryCarbohydrates: {
      shortType: "eatenCarbs",
      expectedUnit: "g",
    },
    HKQuantityTypeIdentifierDietaryFiber: {
      shortType: "eatenFiber",
      expectedUnit: "g",
    },

    HKQuantityTypeIdentifierActiveEnergyBurned: {
      shortType: "energyBurnedActive",
      expectedUnit: "Cal",
    },
    HKQuantityTypeIdentifierBasalEnergyBurned: {
      shortType: "energyBurnedBase",
      expectedUnit: "kcal",
    },
    HKQuantityTypeIdentifierStepCount: {
      shortType: "stepCount",
      expectedUnit: "count",
    },
    HKQuantityTypeIdentifierDistanceWalkingRunning: {
      shortType: "distanceWalking",
      expectedUnit: "mi",
    },
    HKQuantityTypeIdentifierDistanceCycling: {
      shortType: "distanceCycling",
      expectedUnit: "mi",
    },
    HKQuantityTypeIdentifierFlightsClimbed: {
      shortType: "flightsClimbed",
      expectedUnit: "count",
    },
  }

let recordTypeCounts: Record<string, number> = {}
let lastRecordType: string | null = null

const parsedRecords: Array<{type: string; date: string; value: number}> = []

xmlStream.on("tag:record", (record: any) => {
  const recordType: string = record.$attrs?.type ?? "NONE"
  recordTypeCounts[recordType] = (recordTypeCounts[recordType] ?? 0) + 1
  if (lastRecordType && lastRecordType !== recordType) {
    console.log(
      `Read ${recordTypeCounts[lastRecordType]} records of type "${lastRecordType}"`,
    )
  }
  lastRecordType = recordType

  const recordParser = recordParsers[recordType]
  if (!recordParser) return

  const date = record.$attrs.startdate?.split(" ")[0]
  const value = parseFloat(record.$attrs.value)
  const unit = record.$attrs.unit
  if (unit !== recordParser.expectedUnit) {
    throw new Error(
      `Found unit type of "${unit}" but expected "${recordParser.expectedUnit}" when parsing ${recordParser.shortType} record`,
    )
  }
  parsedRecords.push({type: recordParser.shortType, date, value})
})

xmlStream.on("end", () => {
  const outputFile = __dirname + "/output.json"

  writeFileSync(outputFile, JSON.stringify(parsedRecords, null, 2))

  console.log(`Written ${parsedRecords.length} records to ${outputFile}`)
})
