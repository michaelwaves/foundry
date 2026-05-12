"use client"
import { useEffect, useRef } from "react";
import {createPluginUI} from 'molstar/lib/mol-plugin-ui';
import {renderReact18} from 'molstar/lib/mol-plugin-ui/react18';
import {DefaultPluginUISpec} from 'molstar/lib/mol-plugin-ui/spec';
import "molstar/lib/mol-plugin-ui/skin/light.scss";
function MolstarViewer({url}:{url:string}) {
    const parentRef =useRef(null);
    const pluginRef = useRef(null);

    useEffect(()=>{
        let cancelled=false;
        async function init(){
            if(!parentRef.current)return;

            const plugin = await createPluginUI({
                target: parentRef.current,
                render: renderReact18,
                spec: { ...DefaultPluginUISpec(), layout: { initial: { isExpanded: false, showControls: true } } }
            })

             if (cancelled) {
        plugin.dispose();
        return;
      }

            
    pluginRef.current = plugin
        
    const data = await plugin.builders.data.download(
         { url, isBinary: false },
        { state: { isGhost: true } }
      );
      const trajectory = await plugin.builders.structure.parseTrajectory(
        data,
        "mmcif"
      );
      await plugin.builders.structure.hierarchy.applyPreset(
        trajectory,
        "default"
      );
    }


    init();

    return () => {
      cancelled = true;
      pluginRef.current?.dispose();
      pluginRef.current = null;
    };
    },[url])
    return (
        <div ref={parentRef} className="w-full h-full" />
    );
}

export default MolstarViewer;