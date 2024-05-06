import About from "./components/About.jsx";
import Contact from "./components/Contact.jsx";
import Education from "./components/Education.jsx";
import Experience from "./components/Experience.jsx";
import Home from "./components/Home.jsx";
import NavBar from "./components/NavBar.jsx";
import Projects from "./components/Projects.jsx";
import SocialLinks from "./components/SocialLinks.jsx";

function App() {
  return (
    <div>
      <NavBar />
      <Home />
      <About />
      <Projects/>
      <Experience />
      <Education />
      <Contact />
      <SocialLinks />
    </div>
  );
}

export default App;