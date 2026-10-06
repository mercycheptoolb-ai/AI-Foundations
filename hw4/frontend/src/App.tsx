import { Link, Route, Routes } from 'react-router-dom'
import { openChat } from './chatEvents'
import Ticker from './components/Ticker'
import Navbar from './components/Navbar'
import ChatWidget from './components/ChatWidget'
import Home from './pages/Home'
import Products from './pages/Products'
import ProductPage from './pages/ProductPage'
import About from './pages/About'
import Login from './pages/Login'
import Signup from './pages/Signup'
import NotFound from './pages/NotFound'
import { useAuth } from './useAuth'

export default function App() {
  const { user } = useAuth()
  return (
    <>
      <Navbar />
      <Ticker />
      <main className="page">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/products" element={<Products />} />
          <Route path="/products/:productId" element={<ProductPage />} />
          <Route path="/about" element={<About />} />
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
      <footer className="footer">
        <div className="footer-row">
          <span>Campus Customs · 57 Broadway, New Haven, CT</span>
          <span>Officially licensed Yale apparel</span>
        </div>
        <nav className="footer-links" aria-label="Shop by category">
          {[
            ['hoodie', 'Hoodies'],
            ['crewneck', 'Crewnecks'],
            ['t-shirt', 'T-shirts'],
            ['quarter-zip', 'Quarter-zips'],
            ['jacket', 'Jackets'],
            ['long-sleeve', 'Long-sleeves'],
          ].map(([k, label]) => (
            <Link key={k} to={`/products?category=${k}`}>
              {label}
            </Link>
          ))}
          <button type="button" onClick={() => openChat()}>
            Ask the Bulldog Assistant
          </button>
        </nav>
        <div className="footer-wordmark" aria-hidden="true">
          Campus Customs
        </div>
      </footer>
      {/* New key per user: logging in/out starts a fresh chat panel. */}
      <ChatWidget key={user?.id ?? 'guest'} />
    </>
  )
}
