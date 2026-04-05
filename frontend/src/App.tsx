import { BrowserRouter, Route, Routes } from "react-router-dom"

import { LandingPage } from "@/pages/LandingPage"
import { PlanPage } from "@/pages/PlanPage"

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/plan" element={<PlanPage />} />
      </Routes>
    </BrowserRouter>
  )
}
