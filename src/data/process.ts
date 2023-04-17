import {parse} from "csv-parse/sync"
import {readFileSync, writeFileSync} from "node:fs"
import dateRange from "../helpers/dateRange"

const rawData = parse(readFileSync(__dirname + "/unformatted/strong.csv"), {
  columns: true,
})

function getOneRepMax(weight: number, reps: number) {
  return Math.round(weight / (1.0278 - 0.0278 * reps))
}

const trackedExercises: Record<string, string> = {
  "Deadlift (Barbell)": "deadlift",
  "Squat (Barbell)": "squat",
  "Bench Press (Barbell)": "bench",
  "Overhead Press (Barbell)": "overhead",
}

type WorkoutSet = {
  exercise: string
  weight: number
  reps: number
  oneRepMax: number
}

const workouts: Record<string, Array<WorkoutSet>> = {}

for (const item of rawData) {
  const exerciseName = item["Exercise Name"]
  const exercise = trackedExercises[exerciseName]
  if (!exercise) continue

  const date: string = item.Date.split(" ")[0]

  const reps = parseFloat(item.Reps)
  let weight = parseFloat(item.Weight)

  if (date < "2022-03-11" && exerciseName.includes("(Barbell)")) {
    weight = weight - 2.5
  }

  const oneRepMax = getOneRepMax(weight, reps)

  workouts[date] = workouts[date] ?? []
  workouts[date].push({exercise, weight, reps, oneRepMax})
}

const workoutDates = Object.keys(workouts).sort()
const paddedDates = dateRange(
  workoutDates[0],
  workoutDates[workoutDates.length - 1],
)

const data = paddedDates.map((date) => {
  const bestSets: Record<string, WorkoutSet> = {}

  for (const set of workouts[date] ?? []) {
    if (
      !bestSets[set.exercise] ||
      bestSets[set.exercise].oneRepMax < set.oneRepMax
    ) {
      bestSets[set.exercise] = set
    }
  }

  for (const exercise of Object.keys(bestSets)) {
    if (bestSets[exercise].reps >= 10) {
      delete bestSets[exercise]
    }
  }

  const oneRepMaxes = Object.fromEntries(
    Object.values(bestSets).map((set) => [set.exercise, set.oneRepMax]),
  )

  return {date, ...oneRepMaxes}
})

writeFileSync(
  __dirname + "/formatted/oneRepMaxes.json",
  JSON.stringify(data, null, 2),
)
