import React from "react";
import MAX from "../assets/Max.png";
import DANDB from "../assets/DandB.png";
import { experience } from "../data/portfolioData";

const logos = { max: MAX, dnb: DANDB };
const Workexperience = () => (
  <section id="workexperience" className="bg-gradient-to-b from-gray-800 to-black text-white py-12">
    <div className="container max-w-screen-lg mx-auto px-4">
      <h2 className="text-4xl font-bold border-b-4 border-gray-500 pb-4 mb-8">Work Experience</h2>
      <div className="relative">
        <div className="hidden md:block border-l-4 border-gray-500 absolute h-full left-1/2 transform -translate-x-1/2" />
        {experience.map(({ id, organization, role, period, details, logo, link }, index) => (
          <div key={id} className={'mb-8 flex items-center ' + (index % 2 === 0 ? 'md:justify-end' : 'md:justify-start')}>
            <div className={'w-full md:w-1/2 p-2 md:p-4 ' + (index % 2 === 0 ? 'md:pl-12' : 'md:pr-12')}>
              <article className="relative bg-black/50 border border-gray-700 rounded-lg p-6 shadow-md hover:shadow-cyan-700/40 hover:scale-105 duration-500 text-center">
                {logos[logo] ? <img src={logos[logo]} alt={organization + ' logo'} className="w-48 h-28 object-contain rounded-2xl mx-auto mb-3" /> : (
                  <div className="w-48 h-28 mx-auto mb-3 flex items-center justify-center text-2xl font-bold text-cyan-300">PermitTo</div>
                )}
                <h3 className="text-gray-200 text-xl font-semibold mb-2">{organization}</h3>
                <p className="text-cyan-200 mb-1">{role}</p>
                <p className="text-gray-400 text-sm mb-3">{period}</p>
                <p className="text-gray-300 leading-relaxed">{details}</p>
                {link && <a href={link} target="_blank" rel="noopener noreferrer" className="inline-block mt-4 text-cyan-300 hover:underline">Visit website</a>}
              </article>
            </div>
          </div>
        ))}
      </div>
    </div>
  </section>
);
export default Workexperience;
