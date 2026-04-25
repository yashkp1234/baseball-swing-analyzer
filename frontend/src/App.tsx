import { BrowserRouter, Routes, Route } from "react-router-dom";
import { UploadPage } from "@/pages/UploadPage";
import { ResultsPage } from "@/pages/ResultsPage";
import { SwingViewerPage } from "@/pages/SwingViewerPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<UploadPage />} />
        <Route path="/results/:jobId" element={<ResultsPage />} />
        <Route path="/viewer/:jobId" element={<SwingViewerPage />} />
      </Routes>
    </BrowserRouter>
  );
}