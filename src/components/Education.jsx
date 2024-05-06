import React from 'react';
import HKR from "../assets/UNI1.png";
import szabist from "../assets/UNI2.png";

const Education = () => {
  const educationItems = [
    {
      id: 1,
      institution: "Kristianstad University",
      degree: "Bachelor in Software development",
      year: "2022 - 2025",
      imageSrc: HKR, 
      style: "shadow-green-200"

    },
    {
      id: 2,
      institution: "SZABIST",
      degree: "Bachelor of Science in Computer Science",
      year: "2021-2022",
      imageSrc: szabist, 
      style: "shadow-blue-800"
    },
  ];

  return (
    <div id="education" className="bg-gradient-to-b from-gray-800 to-black w-full text-white h-screen">
      <div className="max-w-screen-lg mx-auto p-4 flex flex-col justify-center h-full">
        <div className="pb-8">
          <h2 className="text-4xl font-bold inline border-b-4 border-gray-500">Education</h2>
          <p className="py-6">My educational background</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 px-12 sm:px-0">
          {educationItems.map(({ id, institution, degree, year, imageSrc,style }) => (
            
            <div key={id} className="shadow-md hover:scale-105 duration-500 py-4 rounded-lg bg-gray-700 border-4 border-gray-500">
                
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-xl font-semibold text-gray-300">{institution}</h3>
              </div>
              <img src={imageSrc} alt={institution} className="h-20 w-auto mx-auto mb-4" />
              <p className="text-gray-400 mb-2">{degree}</p>
              <p className="text-gray-400">{year}</p>
              <div className={`shadow-md hover:scale-105 duration-500 py-2 rounded-lg ${style}`}></div>
            </div>
            
          ))}
        </div>
      </div>
    </div>
  );
};

export default Education;
