import { useState, useEffect, useRef, useCallback } from 'react';
import { Link } from 'react-router-dom';
import {
  Brain, Building2, Camera, ChevronRight, Code2, Eye, HardHat,
  Layers, Mail, MapPin, Menu, MessageSquare, Phone, Rocket,
  Shield, Sparkles, TrendingUp, Users, X, Zap, ArrowRight,
  CheckCircle2, Globe, MonitorSmartphone
} from 'lucide-react';

/* ─── Intersection Observer hook ─── */
function useOnScreen(threshold = 0.15) {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) { setVisible(true); obs.unobserve(el); } },
      { threshold }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, [threshold]);
  return { ref, visible };
}

/* ─── Animated counter ─── */
function AnimatedNumber({ target, suffix = '' }: { target: number; suffix?: string }) {
  const [count, setCount] = useState(0);
  const { ref, visible } = useOnScreen(0.3);
  useEffect(() => {
    if (!visible) return;
    let start = 0;
    const duration = 2000;
    const step = (ts: number) => {
      if (!start) start = ts;
      const progress = Math.min((ts - start) / duration, 1);
      setCount(Math.floor(progress * target));
      if (progress < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }, [visible, target]);
  return <span ref={ref}>{count.toLocaleString()}{suffix}</span>;
}

/* ─── Navbar ─── */
function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40);
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  const links = [
    { label: '服務', href: '#services' },
    { label: '優勢', href: '#features' },
    { label: '關於我們', href: '#about' },
    { label: '聯絡', href: '#contact' },
  ];

  return (
    <nav className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${scrolled ? 'glass shadow-lg shadow-black/5' : 'bg-transparent'}`}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16 lg:h-20">
          <a href="#" className="flex items-center gap-2.5 group">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-zhuwei-emerald-500 to-zhuwei-emerald-700 flex items-center justify-center shadow-lg shadow-zhuwei-emerald-500/25 group-hover:shadow-zhuwei-emerald-500/40 transition-shadow">
              <Building2 className="w-5 h-5 text-white" />
            </div>
            <span className="text-lg font-bold text-gray-900 tracking-tight">築未科技</span>
          </a>

          <div className="hidden md:flex items-center gap-1">
            {links.map(l => (
              <a key={l.href} href={l.href} className="px-4 py-2 text-sm font-medium text-gray-600 hover:text-zhuwei-emerald-700 rounded-lg hover:bg-zhuwei-emerald-50/60 transition-all">
                {l.label}
              </a>
            ))}
            <a href="#contact" className="ml-3 px-5 py-2.5 text-sm font-semibold text-white bg-gradient-to-r from-zhuwei-emerald-600 to-zhuwei-emerald-500 rounded-xl hover:shadow-lg hover:shadow-zhuwei-emerald-500/30 hover:-translate-y-0.5 transition-all">
              免費諮詢
            </a>
          </div>

          <button onClick={() => setMobileOpen(!mobileOpen)} className="md:hidden p-2 rounded-lg hover:bg-gray-100 transition-colors">
            {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {mobileOpen && (
        <div className="md:hidden glass border-t border-gray-200/50 animate-fade-in">
          <div className="px-4 py-3 space-y-1">
            {links.map(l => (
              <a key={l.href} href={l.href} onClick={() => setMobileOpen(false)} className="block px-4 py-3 text-sm font-medium text-gray-700 hover:text-zhuwei-emerald-700 hover:bg-zhuwei-emerald-50 rounded-lg transition-colors">
                {l.label}
              </a>
            ))}
            <a href="#contact" onClick={() => setMobileOpen(false)} className="block mt-2 px-4 py-3 text-sm font-semibold text-center text-white bg-gradient-to-r from-zhuwei-emerald-600 to-zhuwei-emerald-500 rounded-xl">
              免費諮詢
            </a>
          </div>
        </div>
      )}
    </nav>
  );
}

/* ─── Hero Section ─── */
function HeroSection() {
  return (
    <section className="relative min-h-screen flex items-center overflow-hidden bg-gradient-to-br from-gray-50 via-white to-zhuwei-emerald-50/30">
      {/* Background decorations */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-[600px] h-[600px] rounded-full bg-gradient-to-br from-zhuwei-emerald-200/30 to-zhuwei-emerald-100/10 blur-3xl animate-float" />
        <div className="absolute -bottom-40 -left-40 w-[500px] h-[500px] rounded-full bg-gradient-to-tr from-zhuwei-emerald-300/20 to-transparent blur-3xl animate-float" style={{ animationDelay: '3s' }} />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] rounded-full bg-gradient-radial from-zhuwei-emerald-100/20 to-transparent blur-3xl" />
        {/* Grid pattern */}
        <div className="absolute inset-0 opacity-[0.03]" style={{ backgroundImage: 'radial-gradient(circle, #059669 1px, transparent 1px)', backgroundSize: '40px 40px' }} />
      </div>

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-24 pb-16 lg:pt-32 lg:pb-24">
        <div className="grid lg:grid-cols-2 gap-12 lg:gap-16 items-center">
          {/* Left content */}
          <div className="space-y-8 animate-fade-in-up">
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-zhuwei-emerald-50 border border-zhuwei-emerald-200/60 text-zhuwei-emerald-700 text-sm font-medium">
              <Sparkles className="w-4 h-4" />
              AI 驅動的營建科技
            </div>

            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black leading-tight tracking-tight text-gray-900">
              用 <span className="gradient-text">人工智慧</span>
              <br />
              築造未來工程
            </h1>

            <p className="text-lg sm:text-xl text-gray-500 leading-relaxed max-w-xl">
              築未科技以 AI 技術賦能營建產業，從智慧工程管理到視覺辨識，
              為您的專案帶來前所未有的效率與精準度。
            </p>

            <div className="flex flex-col sm:flex-row gap-4">
              <a href="#contact" className="group inline-flex items-center justify-center gap-2 px-8 py-4 text-base font-semibold text-white bg-gradient-to-r from-zhuwei-emerald-600 to-zhuwei-emerald-500 rounded-2xl hover:shadow-xl hover:shadow-zhuwei-emerald-500/25 hover:-translate-y-0.5 transition-all">
                開始合作
                <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
              </a>
              <a href="#services" className="group inline-flex items-center justify-center gap-2 px-8 py-4 text-base font-semibold text-gray-700 bg-white border border-gray-200 rounded-2xl hover:border-zhuwei-emerald-300 hover:text-zhuwei-emerald-700 hover:shadow-lg transition-all">
                了解服務
                <ChevronRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
              </a>
            </div>

            {/* Trust badges */}
            <div className="flex items-center gap-6 pt-4">
              <div className="flex items-center gap-2 text-sm text-gray-400">
                <Shield className="w-4 h-4 text-zhuwei-emerald-500" />
                <span>企業級安全</span>
              </div>
              <div className="flex items-center gap-2 text-sm text-gray-400">
                <Zap className="w-4 h-4 text-zhuwei-emerald-500" />
                <span>即時部署</span>
              </div>
              <div className="flex items-center gap-2 text-sm text-gray-400">
                <Globe className="w-4 h-4 text-zhuwei-emerald-500" />
                <span>雲端架構</span>
              </div>
            </div>
          </div>

          {/* Right visual */}
          <div className="relative animate-fade-in" style={{ animationDelay: '0.3s' }}>
            <div className="relative">
              {/* Main card */}
              <div className="relative z-10 rounded-3xl bg-gradient-to-br from-zhuwei-emerald-800 to-zhuwei-emerald-900 p-8 lg:p-10 shadow-2xl shadow-zhuwei-emerald-900/20">
                <div className="space-y-6">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 rounded-2xl bg-zhuwei-emerald-500/20 flex items-center justify-center">
                      <Brain className="w-7 h-7 text-zhuwei-emerald-300" />
                    </div>
                    <div>
                      <div className="text-white font-bold text-lg">Jarvis AI 大腦</div>
                      <div className="text-zhuwei-emerald-300/70 text-sm">智慧工程助理系統</div>
                    </div>
                  </div>

                  <div className="space-y-3">
                    {['工程進度智慧追蹤', 'AI 視覺品質檢測', '自動化報表生成', '即時風險預警'].map((item, i) => (
                      <div key={i} className="flex items-center gap-3 text-zhuwei-emerald-100/80 text-sm">
                        <CheckCircle2 className="w-4 h-4 text-zhuwei-emerald-400 flex-shrink-0" />
                        {item}
                      </div>
                    ))}
                  </div>

                  <div className="pt-2 border-t border-zhuwei-emerald-700/50">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-zhuwei-emerald-300/60">知識庫</span>
                      <span className="text-zhuwei-emerald-200 font-semibold">14,600+ 筆</span>
                    </div>
                    <div className="mt-2 h-2 rounded-full bg-zhuwei-emerald-700/50 overflow-hidden">
                      <div className="h-full w-[85%] rounded-full bg-gradient-to-r from-zhuwei-emerald-400 to-zhuwei-emerald-300" />
                    </div>
                  </div>
                </div>
              </div>

              {/* Floating cards */}
              <div className="absolute -top-4 -right-4 z-20 px-4 py-3 rounded-2xl bg-white shadow-xl shadow-black/5 border border-gray-100 animate-float" style={{ animationDelay: '1s' }}>
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center">
                    <Eye className="w-4 h-4 text-blue-500" />
                  </div>
                  <div>
                    <div className="text-xs font-semibold text-gray-800">視覺辨識</div>
                    <div className="text-[10px] text-gray-400">準確率 96.8%</div>
                  </div>
                </div>
              </div>

              <div className="absolute -bottom-4 -left-4 z-20 px-4 py-3 rounded-2xl bg-white shadow-xl shadow-black/5 border border-gray-100 animate-float" style={{ animationDelay: '2s' }}>
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-lg bg-amber-50 flex items-center justify-center">
                    <TrendingUp className="w-4 h-4 text-amber-500" />
                  </div>
                  <div>
                    <div className="text-xs font-semibold text-gray-800">效率提升</div>
                    <div className="text-[10px] text-gray-400">平均 +340%</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

/* ─── Services Section ─── */
function ServicesSection() {
  const { ref, visible } = useOnScreen();
  const services = [
    {
      icon: Brain,
      title: 'AI 智慧助理',
      desc: '基於大型語言模型的工程專業助理，整合 14,600+ 筆營建知識庫，即時回答工程問題、生成報告。',
      color: 'from-emerald-500 to-teal-500',
      bg: 'bg-emerald-50',
      link: '/services/ai-assistant',
    },
    {
      icon: Eye,
      title: '視覺辨識系統',
      desc: '運用 YOLO + VLM 深度分析技術，自動檢測工地安全、品質缺陷，即時預警並生成標註報告。',
      color: 'from-blue-500 to-cyan-500',
      bg: 'bg-blue-50',
      link: '/services/vision',
    },
    {
      icon: Camera,
      title: '智慧拍照記錄',
      desc: '工程現場拍照自動分類、AI 標註、GPS 定位，一鍵生成施工日誌與進度報告。',
      color: 'from-violet-500 to-purple-500',
      bg: 'bg-violet-50',
      link: '/services/smart-photo',
    },
    {
      icon: Code2,
      title: 'CodeSim 代碼模擬器',
      desc: '線上程式碼執行環境，支援 Python / JavaScript / TypeScript，內建 AI 程式碼分析與優化。',
      color: 'from-orange-500 to-amber-500',
      bg: 'bg-orange-50',
      link: '/services/codesim',
    },
    {
      icon: Layers,
      title: 'MCP 工具生態',
      desc: '26+ 個 MCP 工具整合，涵蓋搜尋、資料庫、地圖、金融、影音等，一站式 AI 工作流。',
      color: 'from-rose-500 to-pink-500',
      bg: 'bg-rose-50',
      link: '/services/mcp-tools',
    },
    {
      icon: MonitorSmartphone,
      title: '遠端監控管理',
      desc: '即時系統監控、遠端截圖、GPU 狀態追蹤，隨時隨地掌握工程系統運行狀況。',
      color: 'from-sky-500 to-indigo-500',
      bg: 'bg-sky-50',
      link: '/services/monitoring',
    },
  ];

  return (
    <section id="services" className="py-24 lg:py-32 bg-white">
      <div ref={ref} className={`max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 section-fade ${visible ? 'visible' : ''}`}>
        <div className="text-center max-w-3xl mx-auto mb-16 lg:mb-20">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-zhuwei-emerald-50 text-zhuwei-emerald-700 text-sm font-medium mb-6">
            <Rocket className="w-4 h-4" />
            核心服務
          </div>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-black text-gray-900 tracking-tight">
            全方位 AI 營建解決方案
          </h2>
          <p className="mt-5 text-lg text-gray-500">
            從工程現場到雲端管理，我們提供完整的 AI 技術棧，讓營建產業邁向智慧化。
          </p>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6 lg:gap-8">
          {services.map((s, i) => (
            <Link
              to={s.link}
              key={i}
              className="group relative p-8 rounded-3xl bg-white border border-gray-100 hover:border-transparent hover:shadow-2xl hover:shadow-gray-200/50 hover:-translate-y-1 transition-all duration-300 no-underline"
              style={{ animationDelay: `${i * 0.1}s` }}
            >
              <div className={`w-14 h-14 rounded-2xl ${s.bg} flex items-center justify-center mb-6 group-hover:scale-110 transition-transform`}>
                <s.icon className={`w-7 h-7 bg-gradient-to-r ${s.color} bg-clip-text`} style={{ color: s.color.includes('emerald') ? '#059669' : s.color.includes('blue') ? '#3b82f6' : s.color.includes('violet') ? '#8b5cf6' : s.color.includes('orange') ? '#f97316' : s.color.includes('rose') ? '#f43f5e' : '#0ea5e9' }} />
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-3">{s.title}</h3>
              <p className="text-gray-500 leading-relaxed text-sm">{s.desc}</p>
              <div className="mt-6 flex items-center gap-1 text-sm font-semibold text-zhuwei-emerald-600 opacity-0 group-hover:opacity-100 transition-opacity">
                了解更多 <ArrowRight className="w-4 h-4" />
              </div>
            </Link>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ─── Features / Why Us Section ─── */
function FeaturesSection() {
  const { ref, visible } = useOnScreen();
  const features = [
    { icon: HardHat, title: '營建專業深耕', desc: '團隊具備豐富營建實務經驗，AI 模型針對台灣營建法規與工程實務深度訓練。' },
    { icon: Shield, title: '企業級安全', desc: 'JWT 認證、角色權限控管、License 離線驗證，資料加密傳輸，符合企業資安標準。' },
    { icon: Zap, title: '智慧路由引擎', desc: '軍師/士兵分工架構，Gemini 負責思考分析，本地 Ollama 負責執行，成本與品質最佳化。' },
    { icon: Users, title: '9 大專業角色', desc: '營建工程師、結構技師、專案管理人等 9 種角色，各自擁有專屬知識庫與系統提示詞。' },
    { icon: Globe, title: '雲端 + 本地混合', desc: '支援 Docker 容器化部署、Cloudflare Tunnel 外網存取，離線模式 7-90 天寬限期。' },
    { icon: TrendingUp, title: '持續自我學習', desc: '每日自動從大模型萃取精華、夜間自主學習，知識庫持續成長，越用越聰明。' },
  ];

  return (
    <section id="features" className="py-24 lg:py-32 bg-gradient-to-b from-gray-50 to-white">
      <div ref={ref} className={`max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 section-fade ${visible ? 'visible' : ''}`}>
        <div className="grid lg:grid-cols-2 gap-16 items-center">
          <div>
            <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-zhuwei-emerald-50 text-zhuwei-emerald-700 text-sm font-medium mb-6">
              <Sparkles className="w-4 h-4" />
              為什麼選擇我們
            </div>
            <h2 className="text-3xl sm:text-4xl lg:text-5xl font-black text-gray-900 tracking-tight leading-tight">
              不只是工具，
              <br />
              <span className="gradient-text">是您的 AI 夥伴</span>
            </h2>
            <p className="mt-5 text-lg text-gray-500 leading-relaxed">
              築未科技不僅提供軟體工具，更以深厚的營建專業知識為基礎，
              打造真正理解工程語言的 AI 系統。
            </p>
            <a href="#contact" className="inline-flex items-center gap-2 mt-8 px-6 py-3 text-sm font-semibold text-white bg-gradient-to-r from-zhuwei-emerald-600 to-zhuwei-emerald-500 rounded-xl hover:shadow-lg hover:shadow-zhuwei-emerald-500/25 transition-all">
              預約展示 <ArrowRight className="w-4 h-4" />
            </a>
          </div>

          <div className="grid sm:grid-cols-2 gap-5">
            {features.map((f, i) => (
              <div key={i} className="p-5 rounded-2xl bg-white border border-gray-100 hover:shadow-lg hover:shadow-gray-100 hover:border-zhuwei-emerald-100 transition-all duration-300">
                <div className="w-10 h-10 rounded-xl bg-zhuwei-emerald-50 flex items-center justify-center mb-4">
                  <f.icon className="w-5 h-5 text-zhuwei-emerald-600" />
                </div>
                <h3 className="font-bold text-gray-900 mb-2">{f.title}</h3>
                <p className="text-sm text-gray-500 leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

/* ─── Stats Section ─── */
function StatsSection() {
  const { ref, visible } = useOnScreen();
  const stats = [
    { value: 14600, suffix: '+', label: '知識庫筆數' },
    { value: 26, suffix: '+', label: 'MCP 工具整合' },
    { value: 9, suffix: '', label: '專業角色' },
    { value: 340, suffix: '%', label: '效率提升' },
  ];

  return (
    <section className="py-20 gradient-bg relative overflow-hidden">
      <div className="absolute inset-0 opacity-10" style={{ backgroundImage: 'radial-gradient(circle, white 1px, transparent 1px)', backgroundSize: '30px 30px' }} />
      <div ref={ref} className={`relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 section-fade ${visible ? 'visible' : ''}`}>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-8 lg:gap-12">
          {stats.map((s, i) => (
            <div key={i} className="text-center">
              <div className="text-4xl sm:text-5xl lg:text-6xl font-black text-white mb-2">
                <AnimatedNumber target={s.value} suffix={s.suffix} />
              </div>
              <div className="text-zhuwei-emerald-200/80 text-sm sm:text-base font-medium">{s.label}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ─── About Section ─── */
function AboutSection() {
  const { ref, visible } = useOnScreen();

  return (
    <section id="about" className="py-24 lg:py-32 bg-white">
      <div ref={ref} className={`max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 section-fade ${visible ? 'visible' : ''}`}>
        <div className="grid lg:grid-cols-2 gap-16 items-center">
          {/* Visual */}
          <div className="relative">
            <div className="rounded-3xl bg-gradient-to-br from-zhuwei-emerald-50 to-zhuwei-emerald-100/50 p-10 lg:p-14">
              <div className="space-y-6">
                <div className="flex items-center gap-4">
                  <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-zhuwei-emerald-500 to-zhuwei-emerald-700 flex items-center justify-center shadow-lg shadow-zhuwei-emerald-500/25">
                    <Building2 className="w-9 h-9 text-white" />
                  </div>
                  <div>
                    <div className="text-2xl font-black text-gray-900">築未科技</div>
                    <div className="text-sm text-gray-500">ZheWei Technology</div>
                  </div>
                </div>
                <div className="h-px bg-gradient-to-r from-zhuwei-emerald-200 to-transparent" />
                <div className="grid grid-cols-2 gap-4">
                  {[
                    { icon: MapPin, label: '嘉義民雄' },
                    { icon: HardHat, label: '營建科技' },
                    { icon: Brain, label: 'AI 驅動' },
                    { icon: Rocket, label: '持續創新' },
                  ].map((item, i) => (
                    <div key={i} className="flex items-center gap-3 p-3 rounded-xl bg-white/80">
                      <item.icon className="w-5 h-5 text-zhuwei-emerald-600" />
                      <span className="text-sm font-medium text-gray-700">{item.label}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Content */}
          <div>
            <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-zhuwei-emerald-50 text-zhuwei-emerald-700 text-sm font-medium mb-6">
              <Building2 className="w-4 h-4" />
              關於我們
            </div>
            <h2 className="text-3xl sm:text-4xl font-black text-gray-900 tracking-tight leading-tight mb-6">
              以科技之力，
              <br />
              築造產業未來
            </h2>
            <div className="space-y-4 text-gray-500 leading-relaxed">
              <p>
                築未科技成立於嘉義民雄，專注於將人工智慧技術應用於營建產業。
                我們相信，傳統產業的數位轉型不應只是口號，而是能真正落地、
                為第一線工程人員帶來實質幫助的解決方案。
              </p>
              <p>
                我們的核心產品 Jarvis AI 大腦，整合了超過 14,600 筆營建專業知識，
                涵蓋施工技術、法規標準、品質管理等面向，並透過持續自主學習不斷進化。
                搭配視覺辨識、智慧路由、MCP 工具生態等技術，為營建產業打造全方位的 AI 解決方案。
              </p>
            </div>
            <div className="mt-8 flex flex-wrap gap-3">
              {['AI 工程助理', '視覺辨識', '知識管理', '自動化報表', '遠端監控'].map(tag => (
                <span key={tag} className="px-4 py-2 rounded-full bg-gray-50 border border-gray-100 text-sm text-gray-600 font-medium">
                  {tag}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

/* ─── Contact Section ─── */
function ContactSection() {
  const { ref, visible } = useOnScreen();
  const [formState, setFormState] = useState({ name: '', email: '', phone: '', company: '', message: '' });
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    setSubmitted(true);
    setTimeout(() => setSubmitted(false), 4000);
  }, []);

  return (
    <section id="contact" className="py-24 lg:py-32 bg-gradient-to-b from-white to-gray-50">
      <div ref={ref} className={`max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 section-fade ${visible ? 'visible' : ''}`}>
        <div className="text-center max-w-3xl mx-auto mb-16">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-zhuwei-emerald-50 text-zhuwei-emerald-700 text-sm font-medium mb-6">
            <MessageSquare className="w-4 h-4" />
            聯絡我們
          </div>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-black text-gray-900 tracking-tight">
            開始您的 AI 轉型之旅
          </h2>
          <p className="mt-5 text-lg text-gray-500">
            無論您是大型營建企業或小型工程團隊，我們都能為您量身打造最適合的解決方案。
          </p>
        </div>

        <div className="grid lg:grid-cols-5 gap-12">
          {/* Contact info */}
          <div className="lg:col-span-2 space-y-8">
            <div>
              <h3 className="text-xl font-bold text-gray-900 mb-6">聯繫方式</h3>
              <div className="space-y-5">
                {[
                  { icon: MapPin, label: '公司地址', value: '嘉義縣民雄鄉' },
                  { icon: Mail, label: '電子郵件', value: 'contact@zhe-wei.net' },
                  { icon: Phone, label: '聯絡電話', value: '洽詢請來信' },
                ].map((item, i) => (
                  <div key={i} className="flex items-start gap-4">
                    <div className="w-11 h-11 rounded-xl bg-zhuwei-emerald-50 flex items-center justify-center flex-shrink-0">
                      <item.icon className="w-5 h-5 text-zhuwei-emerald-600" />
                    </div>
                    <div>
                      <div className="text-sm text-gray-400 mb-0.5">{item.label}</div>
                      <div className="font-medium text-gray-800">{item.value}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="p-6 rounded-2xl bg-gradient-to-br from-zhuwei-emerald-800 to-zhuwei-emerald-900 text-white">
              <h4 className="font-bold text-lg mb-2">免費技術諮詢</h4>
              <p className="text-zhuwei-emerald-200/80 text-sm leading-relaxed">
                我們提供免費的初次技術諮詢，協助您評估 AI 導入的可行性與預期效益。
              </p>
            </div>
          </div>

          {/* Contact form */}
          <div className="lg:col-span-3">
            <form onSubmit={handleSubmit} className="p-8 rounded-3xl bg-white border border-gray-100 shadow-xl shadow-gray-100/50">
              {submitted ? (
                <div className="text-center py-12">
                  <div className="w-16 h-16 rounded-full bg-zhuwei-emerald-50 flex items-center justify-center mx-auto mb-4">
                    <CheckCircle2 className="w-8 h-8 text-zhuwei-emerald-500" />
                  </div>
                  <h3 className="text-xl font-bold text-gray-900 mb-2">感謝您的來信！</h3>
                  <p className="text-gray-500">我們將在 24 小時內回覆您。</p>
                </div>
              ) : (
                <div className="space-y-5">
                  <div className="grid sm:grid-cols-2 gap-5">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">姓名 *</label>
                      <input
                        type="text"
                        required
                        value={formState.name}
                        onChange={e => setFormState(p => ({ ...p, name: e.target.value }))}
                        className="w-full px-4 py-3 rounded-xl border border-gray-200 bg-gray-50/50 text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-zhuwei-emerald-500/20 focus:border-zhuwei-emerald-400 transition-all"
                        placeholder="您的姓名"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">公司名稱</label>
                      <input
                        type="text"
                        value={formState.company}
                        onChange={e => setFormState(p => ({ ...p, company: e.target.value }))}
                        className="w-full px-4 py-3 rounded-xl border border-gray-200 bg-gray-50/50 text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-zhuwei-emerald-500/20 focus:border-zhuwei-emerald-400 transition-all"
                        placeholder="公司名稱"
                      />
                    </div>
                  </div>
                  <div className="grid sm:grid-cols-2 gap-5">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">電子郵件 *</label>
                      <input
                        type="email"
                        required
                        value={formState.email}
                        onChange={e => setFormState(p => ({ ...p, email: e.target.value }))}
                        className="w-full px-4 py-3 rounded-xl border border-gray-200 bg-gray-50/50 text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-zhuwei-emerald-500/20 focus:border-zhuwei-emerald-400 transition-all"
                        placeholder="email@example.com"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">聯絡電話</label>
                      <input
                        type="tel"
                        value={formState.phone}
                        onChange={e => setFormState(p => ({ ...p, phone: e.target.value }))}
                        className="w-full px-4 py-3 rounded-xl border border-gray-200 bg-gray-50/50 text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-zhuwei-emerald-500/20 focus:border-zhuwei-emerald-400 transition-all"
                        placeholder="09xx-xxx-xxx"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">需求描述 *</label>
                    <textarea
                      required
                      rows={4}
                      value={formState.message}
                      onChange={e => setFormState(p => ({ ...p, message: e.target.value }))}
                      className="w-full px-4 py-3 rounded-xl border border-gray-200 bg-gray-50/50 text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-zhuwei-emerald-500/20 focus:border-zhuwei-emerald-400 transition-all resize-none"
                      placeholder="請描述您的需求或想了解的服務..."
                    />
                  </div>
                  <button
                    type="submit"
                    className="w-full py-4 text-base font-semibold text-white bg-gradient-to-r from-zhuwei-emerald-600 to-zhuwei-emerald-500 rounded-xl hover:shadow-lg hover:shadow-zhuwei-emerald-500/25 hover:-translate-y-0.5 transition-all"
                  >
                    送出諮詢
                  </button>
                </div>
              )}
            </form>
          </div>
        </div>
      </div>
    </section>
  );
}

/* ─── Footer ─── */
function SiteFooter() {
  return (
    <footer className="bg-gray-900 text-gray-400 pt-16 pb-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-10 pb-12 border-b border-gray-800">
          {/* Brand */}
          <div className="sm:col-span-2 lg:col-span-1">
            <div className="flex items-center gap-2.5 mb-4">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-zhuwei-emerald-500 to-zhuwei-emerald-700 flex items-center justify-center">
                <Building2 className="w-5 h-5 text-white" />
              </div>
              <span className="text-lg font-bold text-white">築未科技</span>
            </div>
            <p className="text-sm leading-relaxed">
              以 AI 技術賦能營建產業，<br />
              築造智慧工程的未來。
            </p>
          </div>

          {/* Links */}
          <div>
            <h4 className="text-white font-semibold mb-4">服務項目</h4>
            <ul className="space-y-2.5 text-sm">
              {['AI 智慧助理', '視覺辨識系統', '智慧拍照記錄', 'CodeSim 模擬器'].map(item => (
                <li key={item}><a href="#services" className="hover:text-zhuwei-emerald-400 transition-colors">{item}</a></li>
              ))}
            </ul>
          </div>

          <div>
            <h4 className="text-white font-semibold mb-4">公司資訊</h4>
            <ul className="space-y-2.5 text-sm">
              {['關於我們', '技術優勢', '合作夥伴', '聯絡我們'].map(item => (
                <li key={item}><a href="#about" className="hover:text-zhuwei-emerald-400 transition-colors">{item}</a></li>
              ))}
            </ul>
          </div>

          <div>
            <h4 className="text-white font-semibold mb-4">聯絡資訊</h4>
            <ul className="space-y-2.5 text-sm">
              <li className="flex items-center gap-2"><MapPin className="w-4 h-4 text-zhuwei-emerald-500" /> 嘉義縣民雄鄉</li>
              <li className="flex items-center gap-2"><Mail className="w-4 h-4 text-zhuwei-emerald-500" /> contact@zhe-wei.net</li>
              <li className="flex items-center gap-2"><Globe className="w-4 h-4 text-zhuwei-emerald-500" /> zhe-wei.net</li>
            </ul>
          </div>
        </div>

        <div className="pt-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-sm">
          <p>&copy; {new Date().getFullYear()} 築未科技 ZheWei Technology. All rights reserved.</p>
          <div className="flex items-center gap-1 text-xs text-gray-500">
            <Sparkles className="w-3 h-3" /> Powered by AI
          </div>
        </div>
      </div>
    </footer>
  );
}

/* ─── Main Page ─── */
export const HomePage: React.FC = () => {
  return (
    <div className="min-h-screen bg-white">
      <Navbar />
      <HeroSection />
      <ServicesSection />
      <FeaturesSection />
      <StatsSection />
      <AboutSection />
      <ContactSection />
      <SiteFooter />
    </div>
  );
};
