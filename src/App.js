import About from "./components/About.jsx";
import Contact from "./components/Contact.jsx";
import Education from "./components/Education.jsx";
import Experience from "./components/Experience.jsx";
import Home from "./components/Home.jsx";
import NavBar from "./components/NavBar.jsx";
import Projects from "./components/Projects.jsx";
import SocialLinks from "./components/SocialLinks.jsx";
import Workexperience from "./components/Workexperience.jsx";

function App() {
  return (
    <div>
      <NavBar />
      <Home />
      <About />
      <Workexperience />
      <Projects/>
      <Experience />
      <Education />
      <Contact />
      <SocialLinks />
      
    </div>
  );
}

export default App;