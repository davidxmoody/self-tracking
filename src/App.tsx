import {CartesianGrid, Legend, Line, LineChart, XAxis, YAxis} from "recharts"
import oneRepMaxes from "./data/oneRepMaxes.json"
import dateRange from "./helpers/dateRange"

const dataMap: Record<string, Record<string, number>> = {}
let earliest = "9999-99-99"
let latest = "0000-00-00"

for (const item of oneRepMaxes) {
  dataMap[item.date] = dataMap[item.date] ?? {}
  dataMap[item.date][item.exercise] = item.oneRepMax
  if (item.date < earliest) earliest = item.date
  if (item.date > latest) latest = item.date
}

const data = dateRange(earliest, latest).map((date) => {
  return {
    date,
    ...dataMap[date],
  }
})

console.log(data)

export default function App() {
  return (
    <div style={{marginTop: 100}}>
      <LineChart
        width={1200}
        height={500}
        data={data}
        margin={{top: 5, right: 30, left: 20, bottom: 5}}
      >
        <CartesianGrid strokeDasharray="3 3" vertical={true} />
        <XAxis dataKey="date" />
        <YAxis />
        <Legend />
        <Line
          type="monotone"
          dataKey="deadlift"
          stroke="green"
          connectNulls
          dot={false}
        />
        <Line
          type="monotone"
          dataKey="squat"
          stroke="blue"
          connectNulls
          dot={false}
        />
        <Line
          type="monotone"
          dataKey="bench"
          stroke="red"
          connectNulls
          dot={false}
        />
        <Line
          type="monotone"
          dataKey="overhead"
          stroke="orange"
          connectNulls
          dot={false}
        />
      </LineChart>
    </div>
  )
}
