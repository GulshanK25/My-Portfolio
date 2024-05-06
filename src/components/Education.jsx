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
    <div id = "education"className="bg-gradient-to-b from-gray-800 to-black text-white">
      <div className="container px-4 py-8 mx-auto">
        <h2 className="text-4xl font-bold border-b-4 border-gray-500 pb-4 mb-8">Education</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          {educationItems.map(({ id, institution, degree, year, imageSrc, style }) => (
            <div key={id} className={`shadow-md hover:scale-105 duration-500 rounded-lg ${style}`}>
              <div className="flex flex-col items-center justify-center mb-4">
                <img src={imageSrc} alt={institution} className="h-20 w-auto mb-2" />
                <h3 className="text-xl font-semibold text-gray-300">{institution}</h3>
              </div>
              <p className="text-center text-gray-400 mb-2">{degree}</p>
              <p className="text-center text-gray-400">{year}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default Education;
