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

const recordParsers: Record<
  string,
  {shortType: string; expectedUnit: string; sourceNames: string[]}
> = {
  HKQuantityTypeIdentifierBodyMass: {
    shortType: "bodyMassLb",
    expectedUnit: "lb",
    sourceNames: ["Withings"],
  },
  HKQuantityTypeIdentifierBodyFatPercentage: {
    shortType: "bodyFat",
    expectedUnit: "%",
    sourceNames: ["Withings"],
  },
  HKQuantityTypeIdentifierLeanBodyMass: {
    shortType: "leanBodyMassKg",
    expectedUnit: "kg",
    sourceNames: ["Withings"],
  },

  HKQuantityTypeIdentifierDietaryEnergyConsumed: {
    shortType: "eatenCalories",
    expectedUnit: "Cal",
    sourceNames: ["Calorie Counter"],
  },
  HKQuantityTypeIdentifierDietaryProtein: {
    shortType: "eatenProtein",
    expectedUnit: "g",
    sourceNames: ["Calorie Counter"],
  },
  HKQuantityTypeIdentifierDietarySugar: {
    shortType: "eatenSugar",
    expectedUnit: "g",
    sourceNames: ["Calorie Counter"],
  },
  HKQuantityTypeIdentifierDietarySodium: {
    shortType: "eatenSodium",
    expectedUnit: "mg",
    sourceNames: ["Calorie Counter"],
  },
  HKQuantityTypeIdentifierDietaryFatTotal: {
    shortType: "eatenFat",
    expectedUnit: "g",
    sourceNames: ["Calorie Counter"],
  },
  HKQuantityTypeIdentifierDietaryFatSaturated: {
    shortType: "eatenFatSaturated",
    expectedUnit: "g",
    sourceNames: ["Calorie Counter"],
  },
  HKQuantityTypeIdentifierDietaryCarbohydrates: {
    shortType: "eatenCarbs",
    expectedUnit: "g",
    sourceNames: ["Calorie Counter"],
  },
  HKQuantityTypeIdentifierDietaryFiber: {
    shortType: "eatenFiber",
    expectedUnit: "g",
    sourceNames: ["Calorie Counter"],
  },

  HKQuantityTypeIdentifierActiveEnergyBurned: {
    shortType: "energyBurnedActive",
    expectedUnit: "Cal",
    sourceNames: ["David’s Apple Watch"],
  },
  HKQuantityTypeIdentifierBasalEnergyBurned: {
    shortType: "energyBurnedBase",
    expectedUnit: "kcal",
    sourceNames: ["David’s Apple Watch"],
  },
  HKQuantityTypeIdentifierStepCount: {
    shortType: "stepCount",
    expectedUnit: "count",
    sourceNames: ["David’s Apple Watch"],
  },
  HKQuantityTypeIdentifierDistanceWalkingRunning: {
    shortType: "distanceWalking",
    expectedUnit: "mi",
    sourceNames: ["David’s Apple Watch"],
  },
  HKQuantityTypeIdentifierDistanceCycling: {
    shortType: "distanceCycling",
    expectedUnit: "mi",
    sourceNames: ["David’s Apple Watch"],
  },
  HKQuantityTypeIdentifierFlightsClimbed: {
    shortType: "flightsClimbed",
    expectedUnit: "count",
    sourceNames: ["David’s Apple Watch"],
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

  const sourceName: string = record.$attrs.sourcename ?? "unknown"
  if (!recordParser.sourceNames.includes(sourceName)) {
    return
  }

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

// xmlStream.on("tag:workout", (workout: any) => {
//   if (workout.$attrs.workoutactivitytype === "HKWorkoutActivityTypeRunning") {
//     const date = workout.$attrs.startdate?.split(" ")[0]

//     const duration = parseFloat(workout.$attrs.duration)
//     const durationUnit = workout.$attrs.durationunit
//     if (durationUnit !== "min")
//       throw new Error("Encountered unexpected unit type")

//     const distanceItem = workout.$markup.find(
//       (x: any) =>
//         typeof x === "object" &&
//         x.$name === "workoutstatistics" &&
//         x.$attrs.type === "HKQuantityTypeIdentifierDistanceWalkingRunning",
//     )
//     const distance = parseFloat(distanceItem.$attrs.sum)
//     const distanceUnit = distanceItem.$attrs.unit
//     if (distanceUnit !== "mi")
//       throw new Error("Encountered unexpected unit type")

//     const caloriesItem = workout.$markup.find(
//       (x: any) =>
//         typeof x === "object" &&
//         x.$name === "workoutstatistics" &&
//         x.$attrs.type === "HKQuantityTypeIdentifierActiveEnergyBurned",
//     )
//     const calories = parseFloat(caloriesItem.$attrs.sum)
//     const caloriesUnit = caloriesItem.$attrs.unit
//     if (caloriesUnit !== "Cal")
//       throw new Error("Encountered unexpected unit type")

//     console.log(JSON.stringify({date, duration, distance, calories}))
//   }
// })

xmlStream.on("end", () => {
  const outputFile = __dirname + "/output.json"

  writeFileSync(outputFile, JSON.stringify(parsedRecords, null, 2))

  console.log(`Written ${parsedRecords.length} records to ${outputFile}`)
})
