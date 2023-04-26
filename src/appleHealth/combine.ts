import {writeFileSync} from "fs"

const records: Array<{
  type: string
  date: string
  value: number
}> = require("./output.json")

const typesToSum: Record<string, boolean> = {
  energyBurnedActive: true,
  energyBurnedBase: true,
  stepCount: true,
  distanceWalking: true,
  distanceCycling: true,
  flightsClimbed: true,
}

const data: Record<string, Record<string, number>> = {}

for (const record of records) {
  data[record.type] = data[record.type] ?? {}
  if (typesToSum[record.type]) {
    const existingValue = data[record.type][record.date] ?? 0
    data[record.type][record.date] = existingValue + record.value
  } else {
    data[record.type][record.date] = record.value
  }
}

function sortKeys(object: any): any {
  const newObject: any = {}
  for (const key of Object.keys(object).sort()) {
    newObject[key] = object[key]
  }
  return newObject
}

for (const recordType of Object.keys(data)) {
  data[recordType] = sortKeys(data[recordType])
}

writeFileSync(
  __dirname + "/formattedOutput.json",
  JSON.stringify(data, null, 2),
)
