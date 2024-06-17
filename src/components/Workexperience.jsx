import React from 'react';
import MAX from "../assets/Max.png";
import DANDB from "../assets/DandB.png";

const Workexperience = () => {
  const WorkItems = [
    {
      id: 1,
      Organization: "MAX HAMBURGER",
      Role: "Part time worker in the kitchen of MAX Kristianstad",
      Period: "April 2023 - Jun 2024",
      imageSrc: MAX,
      style: "shadow-red-400",
      details: "Worked on preparing food, customer service and learned how to handle things in pressure situation."
    },
    {
      id: 2,
      Organization: "DUN & BRADSTREET",
      Role: "Tech intern",
      Period: "Jun 2024 - Present",
      imageSrc: DANDB,
      style: "shadow-red-400",
      details: "Tech intern working on Angular for frontend development."
    },
  ];

  return (
    <div id="workexperience" className="bg-gradient-to-b from-gray-800 to-black text-white py-8">
      <div className="container mx-auto px-4">
        <h2 className="text-4xl font-bold border-b-4 border-gray-500 pb-4 mb-8">Work Experience</h2>
        <div className="relative">
          <div className="border-l-4 border-gray-500 absolute h-full left-1/2 transform -translate-x-1/2"></div>
          {WorkItems.map(({ id, Organization, Role, Period, imageSrc, style, details }, index) => (
            <div key={id} className={`mb-8 flex justify-${index % 2 === 0 ? 'end' : 'start'} w-full`}>
              <div className={`relative w-full md:w-1/2 p-4 ${index % 2 === 0 ? 'pl-12' : 'pr-12'}`}>
                <div className="absolute top-1/2 transform -translate-y-1/2 bg-gray-500 w-6 h-6 rounded-full left-1/2 -translate-x-1/2"></div>
                <div className={`relative bg-black bg-opacity-50 rounded-lg p-6 shadow-md ${index % 2 === 0 ? 'ml-6' : 'mr-6'}`}>
                  <img src={imageSrc} alt={Organization} className="w-60 h-36 rounded-3xl  mx-auto mb-4" />
                  <h3 className="text-xl font-semibold mb-2 text-gray-300">{Organization}</h3>
                  <p className="text-gray-400 mb-2">{Role}</p>
                  <p className="text-gray-400 mb-2">{Period}</p>
                  <p className="text-gray-400">{details}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default Workexperience;
