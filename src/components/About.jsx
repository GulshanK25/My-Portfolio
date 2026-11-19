import React from "react";
import { profile } from "../data/portfolioData";

const About = () => (
  <section id="about" className="w-full bg-gradient-to-b from-gray-800 to-black text-white py-16 md:py-24">
    <div className="max-w-screen-lg p-4 mx-auto">
      <h2 className="text-4xl font-bold inline border-b-4 border-gray-500">About Me</h2>
      <div className="mt-10 space-y-6">
        {profile.about.map((paragraph, index) => (
          <p key={index} className="text-lg text-gray-300 leading-loose">{paragraph}</p>
        ))}
      </div>
    </div>
  </section>
);
export default About;
