import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { HomePage } from './pages/HomePage';
import { AIAssistantPage } from './pages/services/AIAssistantPage';
import { VisionPage } from './pages/services/VisionPage';
import { SmartPhotoPage } from './pages/services/SmartPhotoPage';
import { CodeSimPage } from './pages/services/CodeSimPage';
import { MCPToolsPage } from './pages/services/MCPToolsPage';
import { MonitoringPage } from './pages/services/MonitoringPage';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/services/ai-assistant" element={<AIAssistantPage />} />
        <Route path="/services/vision" element={<VisionPage />} />
        <Route path="/services/smart-photo" element={<SmartPhotoPage />} />
        <Route path="/services/codesim" element={<CodeSimPage />} />
        <Route path="/services/mcp-tools" element={<MCPToolsPage />} />
        <Route path="/services/monitoring" element={<MonitoringPage />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
