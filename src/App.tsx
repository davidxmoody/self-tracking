import {CartesianGrid, Legend, Line, LineChart, XAxis, YAxis} from "recharts"
import oneRepMaxes from "./data/formatted/oneRepMaxes.json"

export default function App() {
  return (
    <div style={{marginTop: 100}}>
      <LineChart
        width={1200}
        height={500}
        data={oneRepMaxes}
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
