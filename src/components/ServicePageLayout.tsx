import { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, ArrowRight, Building2, ChevronRight } from 'lucide-react';

interface Feature {
  icon: React.ElementType;
  title: string;
  desc: string;
}

interface ServicePageProps {
  title: string;
  subtitle: string;
  description: string;
  icon: React.ElementType;
  color: string;
  bgColor: string;
  features: Feature[];
  highlights?: string[];
  ctaText?: string;
  ctaLink?: string;
  children?: ReactNode;
}

export function ServicePageLayout({
  title, subtitle, description, icon: Icon, color, bgColor,
  features, highlights, ctaText, ctaLink, children
}: ServicePageProps) {
  return (
    <div className="min-h-screen bg-white">
      {/* Navbar */}
      <nav className="fixed top-0 left-0 right-0 z-50 glass shadow-lg shadow-black/5">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16 lg:h-20">
            <Link to="/" className="flex items-center gap-2.5 group">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-zhuwei-emerald-500 to-zhuwei-emerald-700 flex items-center justify-center shadow-lg shadow-zhuwei-emerald-500/25">
                <Building2 className="w-5 h-5 text-white" />
              </div>
              <span className="text-lg font-bold text-gray-900 tracking-tight">築未科技</span>
            </Link>
            <div className="hidden md:flex items-center gap-1">
              <Link to="/" className="px-4 py-2 text-sm font-medium text-gray-600 hover:text-zhuwei-emerald-700 rounded-lg hover:bg-zhuwei-emerald-50/60 transition-all">首頁</Link>
              <Link to="/services/ai-assistant" className="px-4 py-2 text-sm font-medium text-gray-600 hover:text-zhuwei-emerald-700 rounded-lg hover:bg-zhuwei-emerald-50/60 transition-all">AI 助理</Link>
              <Link to="/services/vision" className="px-4 py-2 text-sm font-medium text-gray-600 hover:text-zhuwei-emerald-700 rounded-lg hover:bg-zhuwei-emerald-50/60 transition-all">視覺辨識</Link>
              <Link to="/services/codesim" className="px-4 py-2 text-sm font-medium text-gray-600 hover:text-zhuwei-emerald-700 rounded-lg hover:bg-zhuwei-emerald-50/60 transition-all">CodeSim</Link>
              <a href="/#contact" className="ml-3 px-5 py-2.5 text-sm font-semibold text-white bg-gradient-to-r from-zhuwei-emerald-600 to-zhuwei-emerald-500 rounded-xl hover:shadow-lg hover:shadow-zhuwei-emerald-500/30 hover:-translate-y-0.5 transition-all">
                免費諮詢
              </a>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative pt-28 pb-20 lg:pt-36 lg:pb-28 overflow-hidden bg-gradient-to-br from-gray-50 via-white to-zhuwei-emerald-50/30">
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute -top-40 -right-40 w-[500px] h-[500px] rounded-full bg-gradient-to-br from-zhuwei-emerald-200/20 to-transparent blur-3xl" />
          <div className="absolute inset-0 opacity-[0.02]" style={{ backgroundImage: 'radial-gradient(circle, #059669 1px, transparent 1px)', backgroundSize: '40px 40px' }} />
        </div>
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <Link to="/" className="inline-flex items-center gap-2 text-sm text-gray-500 hover:text-zhuwei-emerald-600 mb-8 transition-colors">
            <ArrowLeft className="w-4 h-4" /> 返回首頁
          </Link>
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div className="space-y-6">
              <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-full ${bgColor} text-sm font-medium`} style={{ color }}>
                <Icon className="w-4 h-4" />
                {subtitle}
              </div>
              <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black leading-tight tracking-tight text-gray-900">
                {title}
              </h1>
              <p className="text-lg sm:text-xl text-gray-500 leading-relaxed max-w-xl">
                {description}
              </p>
              {ctaLink && (
                <a href={ctaLink} className="group inline-flex items-center gap-2 px-8 py-4 text-base font-semibold text-white bg-gradient-to-r from-zhuwei-emerald-600 to-zhuwei-emerald-500 rounded-2xl hover:shadow-xl hover:shadow-zhuwei-emerald-500/25 hover:-translate-y-0.5 transition-all">
                  {ctaText || '立即體驗'}
                  <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                </a>
              )}
            </div>
            <div className="relative">
              <div className="rounded-3xl bg-gradient-to-br from-gray-800 to-gray-900 p-8 lg:p-10 shadow-2xl">
                <div className="flex items-center gap-3 mb-6">
                  <div className="w-12 h-12 rounded-2xl flex items-center justify-center" style={{ backgroundColor: `${color}20` }}>
                    <Icon className="w-7 h-7" style={{ color }} />
                  </div>
                  <div>
                    <div className="text-white font-bold text-lg">{title}</div>
                    <div className="text-gray-400 text-sm">{subtitle}</div>
                  </div>
                </div>
                {highlights && (
                  <div className="space-y-3">
                    {highlights.map((h, i) => (
                      <div key={i} className="flex items-center gap-3 text-gray-300 text-sm">
                        <ChevronRight className="w-4 h-4 flex-shrink-0" style={{ color }} />
                        {h}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-24 lg:py-32 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <h2 className="text-3xl sm:text-4xl font-black text-gray-900 tracking-tight">核心功能</h2>
            <p className="mt-4 text-lg text-gray-500">深入了解我們的技術能力與解決方案</p>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6 lg:gap-8">
            {features.map((f, i) => (
              <div key={i} className="group p-8 rounded-3xl bg-white border border-gray-100 hover:border-transparent hover:shadow-2xl hover:shadow-gray-200/50 hover:-translate-y-1 transition-all duration-300">
                <div className="w-14 h-14 rounded-2xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform" style={{ backgroundColor: `${color}10` }}>
                  <f.icon className="w-7 h-7" style={{ color }} />
                </div>
                <h3 className="text-xl font-bold text-gray-900 mb-3">{f.title}</h3>
                <p className="text-gray-500 leading-relaxed text-sm">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Extra content */}
      {children}

      {/* CTA */}
      <section className="py-20 gradient-bg">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl sm:text-4xl font-black text-white mb-6">準備好開始了嗎？</h2>
          <p className="text-zhuwei-emerald-200/80 text-lg mb-8">聯繫我們，獲取免費技術諮詢與方案評估。</p>
          <a href="/#contact" className="inline-flex items-center gap-2 px-8 py-4 text-base font-semibold text-zhuwei-emerald-900 bg-white rounded-2xl hover:shadow-xl hover:-translate-y-0.5 transition-all">
            免費諮詢 <ArrowRight className="w-5 h-5" />
          </a>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900 text-gray-400 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-sm">
          <p>&copy; {new Date().getFullYear()} 築未科技 ZheWei Technology. All rights reserved.</p>
          <Link to="/" className="text-zhuwei-emerald-400 hover:text-zhuwei-emerald-300 transition-colors">返回首頁</Link>
        </div>
      </footer>
    </div>
  );
}
