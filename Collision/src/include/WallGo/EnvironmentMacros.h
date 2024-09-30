#pragma once

#include "exports_generated.h" // Generated by CMake, shared lib export/import defs

/* Exports are currently not handled: we do not support shared lib builds.
Doing so would require proper hiding ofSTL objects from the public interface (mostly done)
AND manually mark appropriate class members for exporting (not done). */
#define WALLGO_API WALLGO_EXPORT

#define WG_STRINGIFY(x) #x

#ifdef _MSC_VER
    #define WG_PRAGMA(x) __pragma(x)
#else
    #define WG_PRAGMA(x) _Pragma(WG_STRINGIFY(x))
#endif

// Stuff that only works for C++20 and newer. For example: std::sin, std::cos were not constexpr until C++20 
#if __cplusplus >= 202002L
	#define WG_CONSTEXPR20 constexpr
#else 
	#define WG_CONSTEXPR20
#endif

#ifdef NDEBUG
    #define WG_DEBUG 0
#else
    // Is debug build
    #define WG_DEBUG 1
#endif

// Use to silence unused parameter compiler warning
#define WG_UNUSED(expr) do { (void)(expr); } while (0)

// NB: For MSVC the default OMP version is only 2.X, so some newer features may not be available
#if WITH_OMP && _OPENMP >= 200805 // OMP >= 3.0
    #define WG_OMP_SUPPORTS_COLLAPSE 1
#else
    #define WG_OMP_SUPPORTS_COLLAPSE 0
#endif

// OMP atomic read/write is 3.1 feature. If not available, we force a critical section
#if !WITH_OMP
    #define WG_PRAGMA_OMP_ATOMIC_READ
    #define WG_PRAGMA_OMP_ATOMIC_WRITE

#elif _OPENMP >= 201107 // OMP >= 3.1
    #define WG_PRAGMA_OMP_ATOMIC_READ WG_PRAGMA(omp atomic read)
    #define WG_PRAGMA_OMP_ATOMIC_WRITE WG_PRAGMA(omp atomic write)

#else
    #define WG_PRAGMA_OMP_ATOMIC_READ WG_PRAGMA(omp critical)
    #define WG_PRAGMA_OMP_ATOMIC_WRITE WG_PRAGMA(omp critical)

#endif


#if WITH_OMP && _MSC_VER
    /* VS implementation of OMP doesn't allow threadprivate on extern variables.
    See https://stackoverflow.com/questions/12560243/using-threadprivate-directive-in-visual-studio */
    #define WG_THREADPRIVATE_EXTERN_VARIABLE(Type, varName) extern __declspec(thread) Type varName;
    #define WG_INIT_THREADPRIVATE_EXTERN_VARIABLE(Type, varName, value) __declspec(thread) Type varName = value;

#else
    #define WG_THREADPRIVATE_EXTERN_VARIABLE(Type, varName) \
        extern Type varName; \
        WG_PRAGMA(omp threadprivate(varName))

    #define WG_INIT_THREADPRIVATE_EXTERN_VARIABLE(Type, varName, value) \
        Type varName = value; \
        WG_PRAGMA(omp threadprivate(varName))
#endif
