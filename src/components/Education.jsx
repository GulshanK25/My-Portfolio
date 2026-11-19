import React from "react";
import HKR from "../assets/UNI1.png";
import szabist from "../assets/UNI2.png";
import { education } from "../data/portfolioData";

const logos = { hkr: HKR, szabist };
const Education = () => (
  <section id="education" className="bg-gradient-to-b from-gray-800 to-black text-white py-12">
    <div className="container max-w-screen-lg px-4 mx-auto">
      <h2 className="text-4xl font-bold border-b-4 border-gray-500 pb-4 mb-8">Education</h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {education.map(({ id, institution, degree, years, detail, logo }) => (
          <article key={id} className="p-6 shadow-md shadow-green-200/30 hover:shadow-cyan-400 hover:scale-105 duration-500 rounded-lg bg-black/30 text-center">
            {logos[logo] ? (
              <img src={logos[logo]} alt={institution + ' logo'} className="h-20 w-auto mx-auto mb-3 object-contain" />
            ) : (
              <div aria-label="Blekinge Institute of Technology" className="h-20 flex items-center justify-center mb-3 text-3xl font-bold text-cyan-300">BTH</div>
            )}
            <h3 className="text-xl font-semibold text-gray-200 mb-2">{institution}</h3>
            <p className="text-gray-300 mb-1">{degree}</p>
            <p className="text-cyan-300 text-sm mb-3">{years}</p>
            <p className="text-gray-400 text-sm leading-relaxed">{detail}</p>
          </article>
        ))}
      </div>
    </div>
  </section>
);
export default Education;
