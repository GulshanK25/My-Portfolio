import React from "react";

import html from "../assets/html.png";
import css from "../assets/css.png";
import javascript from "../assets/javascript.png";
import reactImage from "../assets/react.png";
import nextjs from "../assets/nextjs.png";
import node from "../assets/node.png";
import graphql from "../assets/graphql.png";
import github from "../assets/github.png";
import tailwind from "../assets/tailwind.png";
import python from "../assets/Python.jpg";
import java from "../assets/Java.png";
import mongodb from "../assets/Mongodb.png";
import mysql from "../assets/mysqllogo.png";
import angular from "../assets/Angular.png";
import postgress from "../assets/postgress.png";

const Experience = () => {
  const techs = [
    {
      id: 1,
      src: html,
      title: "HTML",
      style: "shadow-orange-500",
    },
    {
      id: 2,
      src: css,
      title: "CSS",
      style: "shadow-blue-500",
    },
    {
      id: 3,
      src: javascript,
      title: "JavaScript",
      style: "shadow-yellow-500",
    },
    {
      id: 4,
      src: reactImage,
      title: "React",
      style: "shadow-blue-600",
    },
    {
      id: 5,
      src: tailwind,
      title: "Tailwind",
      style: "shadow-sky-400",
    },
    {
      id: 6,
      src: nextjs,
      title: "Next JS",
      style: "shadow-white",
    },
    {
      id: 7,
      src: node,
      title: "Node",
      style: "shadow-green-300",
    },
    
    {
      id: 8,
      src: graphql,
      title: "GraphQL",
      style: "shadow-pink-400",
    },
    {
      id: 9,
      src: github,
      title: "GitHub",
      style: "shadow-gray-400",
    },
    {
      id: 10,
      src: python,
      title: "python",
      style: "shadow-cyan-800",
    },
    {
      id: 11,
      src: java,
      title: "java",
      style: "shadow-gray-700",
    },
    {
      id: 12,
      src: mongodb,
      title: "mongodb",
      style: "shadow-green-400",
    },
    
    {
      id: 13,
      src: mysql,
      title: "MySQL",
      style: "shadow-blue-400",
    },

    {
      id: 14,
      src: angular,
      title: "Angular",
      style: "shadow-red-400",
    },
    
    {
      id: 15,
      src: postgress,
      title: "postgress",
      style: "shadow-blue-400",
    },
    
    

  ];

  return (
    <div id = "experience" className="bg-gradient-to-b from-gray-800 to-black text-white">
      <div className="container px-4 py-8 mx-auto">
        <h2 className="text-4xl font-bold border-b-4 border-gray-500 pb-4 mb-8">Experience</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-8">
          {techs.map(({ id, src, title, style }) => (
            <div key={id} className={`shadow-md hover:scale-105 duration-500 rounded-lg ${style}`}>
              <img src={src} alt="" className="w-20 mx-auto mt-4 mb-2" />
              <p className="text-center">{title}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default Experience;