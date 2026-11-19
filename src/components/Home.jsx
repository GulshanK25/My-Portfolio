import React from "react";
import Basic from "../assets/mine1.jpg";
import { profile } from "../data/portfolioData";

const secondaryAction = "px-5 py-3 rounded-md border border-gray-500 hover:border-cyan-300 transition-colors font-medium focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-cyan-300";

const Home = () => (
  <section name="home" id="home" className="min-h-screen w-full bg-gradient-to-b from-slate-800 to-black text-white">
    <div className="max-w-screen-lg mx-auto flex flex-col items-center justify-center min-h-screen px-4 pt-24 pb-12 md:flex-row md:gap-12">
      <div className="flex-1">
        <p className="text-cyan-300 font-semibold tracking-wide mb-3">Hello, I'm {profile.name}</p>
        <h1 className="text-4xl sm:text-6xl font-bold text-red-300 leading-tight">{profile.headline}</h1>
        <p className="text-gray-300 py-6 max-w-lg leading-relaxed">{profile.intro}</p>
        <div className="flex flex-wrap gap-3">
          <a href="#projects" className="px-5 py-3 rounded-md bg-cyan-700 hover:bg-cyan-600 transition-colors font-medium focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-cyan-300">Explore Featured Projects</a>
          <a href={profile.resume} download className={secondaryAction}>Download CV</a>
          <a href="#contact" className={secondaryAction}>Contact Me</a>
        </div>
      </div>
      <div className="mt-10 md:mt-0 md:w-2/5">
        <img src={Basic} alt={profile.name} className="rounded-2xl mx-auto w-2/3 md:w-full shadow-lg hover:scale-105 duration-500" />
      </div>
    </div>
  </section>
);
export default Home;
