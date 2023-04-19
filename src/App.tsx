import {
  CartesianGrid,
  Label,
  Legend,
  Line,
  LineChart,
  ReferenceArea,
  XAxis,
  YAxis,
} from "recharts"
import oneRepMaxes from "./data/formatted/oneRepMaxes.json"
import programs from "./data/formatted/programs.json"

const exercises = {
  deadlift: "green",
  squat: "blue",
  bench: "red",
  overhead: "orange",
}

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

        {programs.map((program, i) => (
          <ReferenceArea
            x1={program.start}
            y1={0}
            x2={
              programs[i + 1]?.start ?? oneRepMaxes[oneRepMaxes.length - 1].date
            }
            y2={140}
            stroke="red"
            strokeOpacity={0.3}
          >
            <Label value={program.name} position="insideBottom" />
          </ReferenceArea>
        ))}

        {Object.entries(exercises).map(([exercise, color]) => (
          <Line
            key={exercise}
            dataKey={exercise}
            type="monotone"
            stroke={color}
            connectNulls
            dot={false}
          />
        ))}
      </LineChart>
    </div>
  )
}
